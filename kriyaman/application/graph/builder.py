from langgraph.graph import END, START, StateGraph
from application.graph.nodes import GraphNodes
from application.graph.policies import (
    route_after_acquisition,
    route_after_controller,
    route_after_judge,
)
from application.graph.state import GraphState


def create_kriyaman_graph(nodes: GraphNodes, checkpointer=None):
    """Compile the LangGraph workflow for Kriyamaan Agentic RAG."""
    workflow = StateGraph(GraphState)

    # 1. Register nodes
    workflow.add_node("initialize_run", nodes.initialize_run)
    workflow.add_node("load_session_memory", nodes.load_session_memory)
    workflow.add_node("controller_decide", nodes.controller_decide)
    workflow.add_node("acquisition_stage", nodes.acquisition_stage)
    workflow.add_node("retrieval_agent", nodes.retrieval_agent_node)
    workflow.add_node("evidence_judge", nodes.evidence_judge_node)
    workflow.add_node("controller_refine", nodes.controller_refine_node)

    # Terminal & Generation nodes
    workflow.add_node("clarification_terminal", nodes.clarification_terminal)
    workflow.add_node("abstention_terminal", nodes.abstention_terminal)
    workflow.add_node("conflicting_terminal", nodes.conflicting_terminal)
    workflow.add_node("terminal_ready", nodes.terminal_ready)
    workflow.add_node("context_builder", nodes.context_builder_node)
    workflow.add_node("generate_answer", nodes.generate_answer_node)
    workflow.add_node("persist_turn", nodes.persist_turn_node)

    # 2. Add sequential edges
    workflow.add_edge(START, "initialize_run")
    workflow.add_edge("initialize_run", "load_session_memory")
    workflow.add_edge("load_session_memory", "controller_decide")

    # 3. Add conditional edge from controller_decide
    workflow.add_conditional_edges(
        "controller_decide",
        route_after_controller,
        {
            "clarification_terminal": "clarification_terminal",
            "abstention_terminal": "abstention_terminal",
            "acquisition_stage": "acquisition_stage",
        },
    )

    # 4. Add conditional edge from acquisition_stage
    workflow.add_conditional_edges(
        "acquisition_stage",
        route_after_acquisition,
        {
            "evidence_judge": "evidence_judge",
            "retrieval_agent": "retrieval_agent",
        },
    )

    # 5. retrieval_agent -> evidence_judge
    workflow.add_edge("retrieval_agent", "evidence_judge")

    # 6. Add conditional edge from evidence_judge
    workflow.add_conditional_edges(
        "evidence_judge",
        route_after_judge,
        {
            "terminal_ready": "terminal_ready",
            "clarification_terminal": "clarification_terminal",
            "abstention_terminal": "abstention_terminal",
            "controller_refine": "controller_refine",
            "conflicting_terminal": "conflicting_terminal",
        },
    )

    # 7. controller_refine -> retrieval_agent (bounded loop)
    workflow.add_edge("controller_refine", "retrieval_agent")

    # 8. Generation pipeline: terminal_ready -> context_builder -> generate_answer -> persist_turn -> END
    workflow.add_edge("terminal_ready", "context_builder")
    workflow.add_edge("context_builder", "generate_answer")
    workflow.add_edge("generate_answer", "persist_turn")

    # 9. Terminal persistence: each terminal route executes persist_turn exactly once, then END
    workflow.add_edge("clarification_terminal", "persist_turn")
    workflow.add_edge("abstention_terminal", "persist_turn")
    workflow.add_edge("conflicting_terminal", "persist_turn")
    workflow.add_edge("persist_turn", END)

    return workflow.compile(checkpointer=checkpointer)

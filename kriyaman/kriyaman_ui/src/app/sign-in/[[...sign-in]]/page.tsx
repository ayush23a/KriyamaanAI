import { SignIn } from '@clerk/nextjs';
import Image from 'next/image';
import Link from 'next/link';

export default function SignInPage() {
  return (
    <div className="grid min-h-screen lg:grid-cols-2 bg-[#FAF8F5]">
      {/* Left Column: Kriyamaan Branding & Clerk SignIn */}
      <div className="flex flex-col justify-between p-6 sm:p-10 lg:p-14">
        {/* Brand Header */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-[#C25E43] flex items-center justify-center text-white shadow-sm font-serif font-bold text-lg group-hover:bg-[#a94f37] transition-colors">
              K
            </div>
            <div className="flex flex-col">
              <span className="font-serif text-lg font-semibold tracking-tight text-stone-900 leading-none">
                Kriyamaan
              </span>
              <span className="text-[10px] tracking-widest uppercase font-mono text-stone-600 mt-0.5">
                Research Studio
              </span>
            </div>
          </Link>
        </div>

        {/* Center: Sign-In Container */}
        <div className="w-full max-w-[420px] mx-auto py-10 flex flex-col items-center">
          <div className="w-full mb-6 text-center">
            <h1 className="font-serif text-2xl font-bold tracking-tight text-stone-900">
              Welcome to Kriyamaan
            </h1>
            <p className="text-sm text-stone-600 mt-1">
              Deterministic agentic research with verified citations.
            </p>
          </div>

          <SignIn
            path="/sign-in"
            routing="path"
            signUpUrl="/sign-up"
            appearance={{
              elements: {
                rootBox: 'w-full shadow-none',
                card: 'bg-white border border-stone-200/80 rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.04)] p-6 sm:p-8',
                headerTitle: 'hidden',
                headerSubtitle: 'hidden',
                formButtonPrimary:
                  'bg-[#C25E43] hover:bg-[#a94f37] text-white font-medium text-sm rounded-lg transition-colors py-2.5 shadow-sm',
                formFieldInput:
                  'rounded-lg border-stone-200 bg-white text-stone-900 focus:border-[#C25E43] focus:ring-1 focus:ring-[#C25E43] text-sm',
                formFieldLabel: 'text-xs font-medium text-stone-700 font-sans',
                footerActionLink: 'text-[#C25E43] hover:text-[#a94f37] font-medium text-sm',
                identityPreviewText: 'text-stone-900 font-medium',
                identityPreviewEditButton: 'text-[#C25E43] hover:text-[#a94f37]',
                socialButtonsBlockButton:
                  'border border-stone-200 hover:bg-stone-50 text-stone-800 rounded-lg text-sm font-medium transition-colors',
                dividerLine: 'bg-stone-200',
                dividerText: 'text-xs text-stone-600 uppercase tracking-wider font-mono',
              },
              variables: {
                colorPrimary: '#C25E43',
                colorForeground: '#1C1917',
                colorMutedForeground: '#78716C',
                colorBackground: '#FFFFFF',
                borderRadius: '0.5rem',
                fontFamily: '"Plus Jakarta Sans", sans-serif',
              },
            }}
          />
        </div>

        {/* Footer info */}
        <div className="text-center text-xs text-stone-600 font-mono">
          <span>Staging Build · Isolated User Workspace · Zero Data Leaks</span>
        </div>
      </div>

      {/* Right Column: Editorial Visual Cover */}
      <div className="relative hidden lg:block overflow-hidden bg-stone-900 border-l border-stone-200/60">
        <Image
          src="/login-cover.jpg"
          alt="Kriyamaan structured intelligence and verified research repository"
          fill
          priority
          sizes="50vw"
          className="object-cover opacity-90 transition-opacity duration-700"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-stone-950/70 via-stone-950/20 to-transparent" />
        
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/15 text-[11px] font-mono uppercase tracking-widest text-stone-200 mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#E07A5F]" />
            Deterministic RAG Engine
          </div>
          <h2 className="font-serif text-2xl xl:text-3xl font-bold tracking-tight leading-snug max-w-lg">
            Evidence-grounded synthesis with cryptographic audit trails.
          </h2>
          <p className="mt-3 text-sm text-stone-300 max-w-md font-sans leading-relaxed">
            Every conclusion is evaluated against retrieved evidence gates. Autonomous agent execution with strict user boundaries and deterministic verification.
          </p>
        </div>
      </div>
    </div>
  );
}

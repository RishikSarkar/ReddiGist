'use client';
import { signIn } from "next-auth/react";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";

export default function SignIn() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.push(callbackUrl);
    }
  }, [status, router, callbackUrl]);

  const handleSignIn = async () => {
    setIsLoading(true);
    await signIn("google", { callbackUrl });
  };

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="min-h-screen bg-[#0e1113] text-white flex items-center justify-center">
        <div className="animate-pulse text-xl text-[#D93900]">Loading...</div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#0e1113] text-white flex flex-col items-center justify-center p-8">
      <div className="max-w-md w-full bg-[#1A1A1B] p-8 rounded-lg border border-[#333D42] shadow-xl">
        <h1 className="text-4xl font-bold mb-8 text-[#D93900] text-center">ReddiGist</h1>
        
        <p className="text-gray-300 mb-8 text-center">
          Sign in to save your searches and access your personalized ReddiGist dashboard.
        </p>
        
        <button
          onClick={handleSignIn}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-3 bg-[#272729] hover:bg-[#333333] text-white py-3 px-4 rounded-lg border border-[#333D42] transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
          </svg>
          {isLoading ? "Signing in..." : "Sign in with Google"}
        </button>
        
        <div className="mt-4 text-center">
          <button
            onClick={() => router.push('/')}
            className="text-gray-400 hover:text-gray-300 text-sm underline transition-colors"
          >
            Continue as guest
          </button>
        </div>
      </div>
    </main>
  );
} 
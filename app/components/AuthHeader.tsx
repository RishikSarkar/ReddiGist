'use client';
import { signIn, signOut, useSession } from "next-auth/react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";

export default function AuthHeader() {
  const { data: session, status } = useSession();
  const router = useRouter();
  
  const handleSignIn = async () => {
    const result = await signIn("google", { redirect: false, callbackUrl: "/" });
    
    if (result?.url) {
      window.open(result.url, "_blank", "noopener,noreferrer");
    }
  };
  
  return (
    <div className="w-full flex items-center mb-16 relative">
      <button
        onClick={() => router.push('/signin')}
        className="flex items-center gap-2 bg-[#272729] hover:bg-[#333333] text-gray-300 py-2 px-4 rounded-lg border border-[#333D42] transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
        Home
      </button>
      
      <div className="absolute left-1/2 transform -translate-x-1/2">
        <Link href="/" className="text-4xl font-bold text-[#D93900]">
          ReddiGist
        </Link>
      </div>
      
      <div className="ml-auto">
        {status === "authenticated" ? (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              {session.user?.image && (
                <div className="relative w-8 h-8 rounded-full overflow-hidden">
                  <Image 
                    src={session.user.image}
                    alt={session.user.name || "User"} 
                    fill
                    className="object-cover"
                  />
                </div>
              )}
              <span className="text-gray-300 text-sm hidden md:inline">
                {session.user?.name}
              </span>
            </div>
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="flex items-center gap-2 bg-[#272729] hover:bg-[#333333] text-gray-300 py-2 px-4 rounded-lg border border-[#333D42] transition-colors"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <button
            onClick={handleSignIn}
            className="flex items-center gap-2 bg-[#272729] hover:bg-[#333333] text-white py-2 px-4 rounded-lg border border-[#333D42] transition-colors"
          >
            <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Sign In
          </button>
        )}
      </div>
    </div>
  );
} 
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function UsersRedirect() {
  const router = useRouter();
  
  useEffect(() => {
    router.replace("/iam");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-600">Redirecting to IAM...</p>
    </div>
  );
}

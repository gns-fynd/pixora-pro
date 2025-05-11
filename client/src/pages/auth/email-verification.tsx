import { Link, useLocation } from "react-router-dom";
import { AuthLayout } from "./auth-layout";
import { IconMail, IconArrowRight } from "@tabler/icons-react";

export default function EmailVerification() {
  const location = useLocation();
  const email = location.state?.email || "";
  return (
    <AuthLayout>
      <div className="w-full text-center">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
            <IconMail className="h-8 w-8 text-primary" />
          </div>
        </div>
        
        <h1 className="text-2xl font-bold mb-2">Check your email</h1>
        
        <p className="text-foreground/60 text-sm mb-6">
          We've sent a verification link to{" "}
          <span className="font-medium text-foreground">{email || "your email address"}</span>.
          Please check your inbox and click the link to verify your account.
        </p>
        
        <div className="bg-white/5 border border-white/10 rounded-lg p-4 mb-6">
          <p className="text-sm text-foreground/80">
            <strong>Note:</strong> You need to verify your email before you can sign in.
            The verification link will expire in 24 hours.
          </p>
        </div>
        
        <div className="flex flex-col gap-4">
          <Link
            to="/auth"
            className="flex items-center justify-center gap-2 py-2.5 px-4 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium transition-colors"
          >
            Return to Sign In
            <IconArrowRight size={18} />
          </Link>
          
          <p className="text-xs text-foreground/40">
            Didn't receive the email? Check your spam folder or{" "}
            <Link to="/auth/sign-up" className="text-primary hover:text-primary/80">
              try again with a different email
            </Link>
            .
          </p>
        </div>
      </div>
    </AuthLayout>
  );
}

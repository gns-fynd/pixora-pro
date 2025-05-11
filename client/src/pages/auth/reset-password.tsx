import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Link } from "react-router-dom";
import { AuthLayout } from "./auth-layout";
import useAuthStore from "@/store/use-auth-store";
import { IconMail } from "@tabler/icons-react";

// Form schema for password reset
const resetPasswordSchema = z.object({
  email: z
    .string({
      required_error: "Email is required",
    })
    .email("Please enter a valid email"),
});

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export default function ResetPassword() {
  const { resetPassword, error, isLoading } = useAuthStore();
  const [isSubmitted, setIsSubmitted] = useState(false);
  
  // Initialize form with validation
  const form = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  // Handle form submission
  async function onSubmit(values: ResetPasswordFormValues) {
    await resetPassword(values.email);
    if (!error) {
      setIsSubmitted(true);
    }
  }

  return (
    <AuthLayout>
      <div className="w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">Reset your password</h1>
          <p className="text-foreground/60 text-sm">
            Enter your email and we'll send you a link to reset your password
          </p>
        </div>

        {/* Success message */}
        {isSubmitted && !error && (
          <div className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
            <p className="text-green-500 text-sm">
              If an account exists with this email, we've sent a password reset link. Please check your inbox.
            </p>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-red-500 text-sm">{error}</p>
          </div>
        )}

        {/* Reset password form */}
        {!isSubmitted && (
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            {/* Email field */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium block">
                Email
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-foreground/60">
                  <IconMail size={18} />
                </div>
                <input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white/5 border border-white/10 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 outline-none transition"
                  {...form.register("email")}
                />
              </div>
              {form.formState.errors.email && (
                <p className="text-red-500 text-xs mt-1">
                  {form.formState.errors.email.message}
                </p>
              )}
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}

        {/* Back to sign in */}
        <div className="mt-8 text-center">
          <Link to="/auth" className="text-primary hover:text-primary/80 font-medium text-sm">
            Back to sign in
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
}

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { AuthLayout } from "./auth-layout";
import useAuthStore from "@/store/use-auth-store";
import { 
  IconBrandGoogle, 
  IconBrandApple, 
  IconMail, 
  IconLock, 
  IconEye, 
  IconEyeOff,
  IconUser
} from "@tabler/icons-react";

// Form schema for sign up
const signUpSchema = z.object({
  name: z
    .string({
      required_error: "Name is required",
    })
    .min(2, "Name must be at least 2 characters"),
  email: z
    .string({
      required_error: "Email is required",
    })
    .email("Please enter a valid email"),
  password: z
    .string({
      required_error: "Password is required",
    })
    .min(6, "Password must be at least 6 characters"),
  confirmPassword: z
    .string({
      required_error: "Please confirm your password",
    })
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type SignUpFormValues = z.infer<typeof signUpSchema>;

export default function SignUp() {
  const navigate = useNavigate();
  const { signUp, signInWithGoogle, signInWithApple, error, isLoading } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  // Initialize form with validation
  const form = useForm<SignUpFormValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  // Handle form submission
  async function onSubmit(values: SignUpFormValues) {
    await signUp(values.email, values.password);
    if (!error) {
      // After successful signup, navigate to email verification page
      navigate('/auth/email-verification', { 
        state: { email: values.email } 
      });
    }
  }

  // Toggle password visibility
  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  // Toggle confirm password visibility
  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(!showConfirmPassword);
  };

  return (
    <AuthLayout>
      <div className="w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">Create an account</h1>
          <p className="text-foreground/60 text-sm">
            Sign up to get started with Pixora AI
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-red-500 text-sm">{error}</p>
          </div>
        )}

        {/* Sign up form */}
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
          {/* Name field */}
          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium block">
              Full Name
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-foreground/60">
                <IconUser size={18} />
              </div>
              <input
                id="name"
                type="text"
                placeholder="John Doe"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-background/5 border border-border/20 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 outline-none transition"
                {...form.register("name")}
              />
            </div>
            {form.formState.errors.name && (
              <p className="text-red-500 text-xs mt-1">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>

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
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-background/5 border border-border/20 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 outline-none transition"
                {...form.register("email")}
              />
            </div>
            {form.formState.errors.email && (
              <p className="text-red-500 text-xs mt-1">
                {form.formState.errors.email.message}
              </p>
            )}
          </div>

          {/* Password field */}
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium block">
              Password
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-foreground/60">
                <IconLock size={18} />
              </div>
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                className="w-full pl-10 pr-10 py-2.5 rounded-lg bg-background/5 border border-border/20 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 outline-none transition"
                {...form.register("password")}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-foreground/60 hover:text-foreground/80"
                onClick={togglePasswordVisibility}
              >
                {showPassword ? <IconEyeOff size={18} /> : <IconEye size={18} />}
              </button>
            </div>
            {form.formState.errors.password && (
              <p className="text-red-500 text-xs mt-1">
                {form.formState.errors.password.message}
              </p>
            )}
          </div>

          {/* Confirm Password field */}
          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium block">
              Confirm Password
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-foreground/60">
                <IconLock size={18} />
              </div>
              <input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                placeholder="••••••••"
                className="w-full pl-10 pr-10 py-2.5 rounded-lg bg-background/5 border border-border/20 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 outline-none transition"
                {...form.register("confirmPassword")}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-foreground/60 hover:text-foreground/80"
                onClick={toggleConfirmPasswordVisibility}
              >
                {showConfirmPassword ? <IconEyeOff size={18} /> : <IconEye size={18} />}
              </button>
            </div>
            {form.formState.errors.confirmPassword && (
              <p className="text-red-500 text-xs mt-1">
                {form.formState.errors.confirmPassword.message}
              </p>
            )}
          </div>

          {/* Sign up button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 px-4 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Creating account..." : "Create account"}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border/20"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-foreground/60">or continue with</span>
          </div>
        </div>

        {/* Social sign in buttons */}
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => signInWithGoogle()}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 py-2.5 px-4 bg-background/5 hover:bg-background/10 border border-border/20 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <IconBrandGoogle size={18} />
            <span>Google</span>
          </button>
          <button
            type="button"
            onClick={() => signInWithApple()}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 py-2.5 px-4 bg-background/5 hover:bg-background/10 border border-border/20 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <IconBrandApple size={18} />
            <span>Apple</span>
          </button>
        </div>

        {/* Sign in link */}
        <p className="mt-8 text-center text-sm text-foreground/60">
          Already have an account?{" "}
          <Link to="/auth" className="text-primary hover:text-primary/80 font-medium">
            Sign in
          </Link>
        </p>

        {/* Terms and privacy */}
        <p className="mt-4 text-center text-xs text-foreground/40">
          By signing up, you agree to our{" "}
          <Link to="/terms" className="text-foreground/60 hover:text-foreground/80">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link to="/privacy" className="text-foreground/60 hover:text-foreground/80">
            Privacy Policy
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}

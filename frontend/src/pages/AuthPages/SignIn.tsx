import { useEffect } from "react";
import { Navigate } from "react-router";
import toast from "react-hot-toast";
import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";
import SignInForm from "../../components/auth/SignInForm";
import { useAuth } from "../../hooks/useAuth";
import { SIGNED_OUT_REASON_KEY } from "../../hooks/useIdleTimeout";

export default function SignIn() {
  const { isAuthenticated, user } = useAuth();

  // Signed out for inactivity (set by AppLayout; kept in sessionStorage so it survives a page reload)
  useEffect(() => {
    const reason = sessionStorage.getItem(SIGNED_OUT_REASON_KEY);
    if (reason === "idle") {
      sessionStorage.removeItem(SIGNED_OUT_REASON_KEY);
      toast.error("Session expired due to inactivity. Please login again.", { id: "idle-signout" });
    } else if (reason === "login-disabled") {
      sessionStorage.removeItem(SIGNED_OUT_REASON_KEY);
      toast.error("Sign-in has been switched off for your role at this institution.", { id: "login-disabled" });
    }
  }, []);

  // The installed app (PWA) opens at /signin: someone already signed in goes straight to the dashboard.
  // (Not gated on `loading`: that flag is also true while the login request runs, and would unmount the form.)
  if (isAuthenticated && user) return <Navigate to="/dashboard" replace />;

  return (
    <>
      <PageMeta
        title="Sign In | EduSpyre - Education Management System"
        description="Sign in page - EduSpyre Education Management System"
      />
      <AuthLayout>
        <SignInForm />
      </AuthLayout>
    </>
  );
}

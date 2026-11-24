import { Navigate } from "react-router";
import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";
import SignInForm from "../../components/auth/SignInForm";
import { useAuth } from "../../hooks/useAuth";

export default function SignIn() {
  const { isAuthenticated, user } = useAuth();

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

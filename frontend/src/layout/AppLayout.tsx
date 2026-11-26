import { SidebarProvider, useSidebar } from "../context/SidebarContext";
import { Link, Outlet, useLocation } from "react-router";
import { EmptyState } from "../components";
import { FEATURE_LABELS, featureForPath, hasFeature } from "../config/features";
import { useAuthStore } from "../stores/authStore";
import AppHeader from "./AppHeader";
import Backdrop from "./Backdrop";
import AppSidebar from "./AppSidebar";
import { useIdleTimeout } from "../hooks/useIdleTimeout";
import { isInstalledOnPhoneOrTablet } from "../components/pwa/platform";
import { useRoleRefresh } from "../hooks/useRoleRefresh";
import { usePageRefresh } from "../hooks/usePageRefresh";
import { useAuth } from "../hooks/useAuth";
import { SIGNED_OUT_REASON_KEY } from "../hooks/useIdleTimeout";

const LayoutContent: React.FC = () => {
  useRoleRefresh(); // menu follows role tick-box changes within a minute
  const refreshKey = usePageRefresh();
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();
  const { logout, isAuthenticated } = useAuth();
  // A page whose feature the Super Admin hasn't switched on for this institution isn't opened
  const { pathname } = useLocation();
  const features = useAuthStore((s) => s.user?.features);
  const role = useAuthStore((s) => s.user?.role);
  const pageFeature = featureForPath(pathname, role);
  const switchedOff = !!pageFeature && !hasFeature(features, pageFeature);

  // Auto-logout after 15 minutes of inactivity - in a browser tab or an app installed on a computer.
  // The installed app on a phone/tablet is the person's own device: it stays signed in (so notifications keep coming).
  useIdleTimeout({
    timeout: 15 * 60 * 1000,
    enabled: isAuthenticated && !isInstalledOnPhoneOrTablet(),
    onIdle: () => {
      // The sign-in page shows the message: requests still in flight can fail after the logout and
      // reload the page (forceLogout), which would wipe a toast shown from here.
      sessionStorage.setItem(SIGNED_OUT_REASON_KEY, "idle");
      logout();
    },
  });

  return (
    <div className="min-h-screen xl:flex">
      <div>
        <AppSidebar />
        <Backdrop />
      </div>
      <div
        className={`flex-1 min-w-0 transition-all duration-300 ease-in-out ${
          isExpanded || isHovered ? "lg:ml-[290px]" : "lg:ml-[90px]"
        } ${isMobileOpen ? "ml-0" : ""}`}
      >
        <AppHeader />
        <div className="p-4 mx-auto max-w-(--breakpoint-2xl) md:p-6 overflow-x-hidden">
          {/* key changes on refresh (button / returning to the installed app) -> the page loads its data again */}
          {switchedOff && pageFeature ? (
            <EmptyState
              title={`${FEATURE_LABELS[pageFeature]} isn't switched on`}
              description="This feature isn't part of your institution's setup. Ask your institution admin if you need it."
              action={<Link to="/dashboard" className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">Back to Dashboard</Link>}
            />
          ) : (
            <Outlet key={refreshKey} />
          )}
        </div>
      </div>
    </div>
  );
};

const AppLayout: React.FC = () => {
  return (
    <SidebarProvider>
      <LayoutContent />
    </SidebarProvider>
  );
};

export default AppLayout;

import "./landing.css";
import PageMeta from "../../components/common/PageMeta";
import CapabilityStrip from "./components/CapabilityStrip";
import ContactSection from "./components/ContactSection";
import CtaSection from "./components/CtaSection";
import FaqSection from "./components/FaqSection";
import FeaturesSection from "./components/FeaturesSection";
import HeroSection from "./components/HeroSection";
import HowItWorksSection from "./components/HowItWorksSection";
import LandingFooter from "./components/LandingFooter";
import LandingNavbar from "./components/LandingNavbar";
import MobileAppSection from "./components/MobileAppSection";
import RolesSection from "./components/RolesSection";

/** Public marketing / entry page shown at "/". The login page lives at "/signin". */
export default function LandingPage() {
  return (
    <>
      <PageMeta
        title="EduSpyre | Smart Education Management System"
        description="EduSpyre brings attendance, timetables, exams, fees, AI-assisted homework and campus transport together, with a tailored dashboard for administrators, teachers, parents and students."
      />
      <div className="relative z-1 min-h-screen overflow-x-clip bg-white text-gray-900 antialiased dark:bg-gray-950 dark:text-white">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-brand-600 focus:shadow-lg"
        >
          Skip to content
        </a>
        <LandingNavbar />
        <main id="main-content">
          <HeroSection />
          <CapabilityStrip />
          <FeaturesSection />
          <RolesSection />
          <MobileAppSection />
          <HowItWorksSection />
          <FaqSection />
          <ContactSection />
          <CtaSection />
        </main>
        <LandingFooter />
      </div>
    </>
  );
}

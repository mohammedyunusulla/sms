import { Link } from "react-router";
import BrandLogo from "../common/BrandLogo";

/** Centred Edusphere logo above auth form headings, shown where the brand panel is hidden (< lg). */
export default function AuthMobileLogo() {
  return (
    <Link
      to="/"
      aria-label="Edusphere home"
      className="mx-auto mb-5 flex w-fit rounded-lg focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/20 short:mb-3 very-short:mb-2 lg:hidden"
    >
      <BrandLogo className="h-10 short:h-8 very-short:h-7" />
    </Link>
  );
}

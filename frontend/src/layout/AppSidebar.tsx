import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router";
import { usePermissions } from "../hooks/usePermissions";

// Assume these icons are imported from an icon library
import { useSidebar } from "../context/SidebarContext";
import {
    BoxCubeIcon,
    CalenderIcon,
    ChevronDownIcon,
    GridIcon,
    ListIcon,
    PageIcon,
    PieChartIcon,
    PlugInIcon,
    TableIcon,
    TaskIcon,
    UserCircleIcon
} from "../icons";
import { SIDEBAR_PERMISSION_MAP, isPathHiddenForRole } from "../config/permissions";
import { isPageSwitchedOff } from "../config/features";
import { useAuthStore } from "../stores/authStore";
// import SidebarWidget from "./SidebarWidget";

type NavItem = {
    name: string;
    icon: React.ReactNode;
    section?: string; // heading the item is listed under (SECTION_ORDER); none = top, no heading
    path?: string;
    subItems?: { name: string; path: string; pro?: boolean; new?: boolean }[];
};

// Sidebar headings, in the order they are shown. A heading only appears for a
// person when at least one of its items is visible to them.
const SECTION_ORDER = [
    "Academics",
    "Attendance & Leave",
    "Communication",
    "Finance & Transport",
    "Administration",
];

// Items are shown in this order inside their section. Who sees what is decided
// by SIDEBAR_PERMISSION_MAP (config/permissions.ts), keyed by `name`.
const allMenuItems: NavItem[] = [
    // Dashboard (All roles)
    {
        icon: <GridIcon />,
        name: "Dashboard",
        path: "/dashboard",
    },

    // ---------------- Academics ----------------
    // Class Management (InstitutionAdmin, Principal)
    {
        icon: <PageIcon />,
        name: "Class Management",
        section: "Academics",
        subItems: [
            { name: "Classes", path: "/classes", pro: false },
            { name: "Rooms", path: "/rooms", pro: false },
        ],
    },
    // Academics Management (InstitutionAdmin, Principal, Teacher)
    {
        icon: <PlugInIcon />,
        name: "Academics Management",
        section: "Academics",
        subItems: [
            { name: "Subjects", path: "/academics/subjects", pro: false },
            { name: "Assign Subjects", path: "/academics/assign-subjects", pro: false },
            { name: "Marks Entry", path: "/academics/marks/entry", pro: false },
            { name: "Class Progress", path: "/academics/progress/class", pro: false },
        ],
    },
    // Syllabus Management (InstitutionAdmin, Principal, Teacher)
    {
        icon: <PageIcon />,
        name: "Syllabus Management",
        section: "Academics",
        subItems: [
            { name: "All Syllabi", path: "/syllabus", pro: false },
            { name: "Analytics", path: "/syllabus/analytics", pro: false },
            { name: "My Syllabus Progress", path: "/syllabus/my-progress", pro: false },
        ],
    },
    // Syllabus – Parent (linked child)
    {
        icon: <PageIcon />,
        name: "My Child's Syllabus",
        section: "Academics",
        path: "/parent/syllabus",
    },
    // Timetable (InstitutionAdmin, Principal, Teacher)
    {
        icon: <CalenderIcon />,
        name: "Timetable",
        section: "Academics",
        path: "/timetable",
    },
    // Timetable – Student (own schedule)
    {
        icon: <CalenderIcon />,
        name: "My Timetable",
        section: "Academics",
        path: "/timetable/my-timetable",
    },
    // Timetable – Parent (linked child)
    {
        icon: <CalenderIcon />,
        name: "My Child's Timetable",
        section: "Academics",
        path: "/parent/timetable",
    },
    // Substitute teacher planner - timetable managers
    {
        icon: <CalenderIcon />,
        name: "Substitutions",
        section: "Academics",
        path: "/substitutions",
    },
    // Assignments – Teacher / Admin
    {
        icon: <ListIcon />,
        name: "Assignments",
        section: "Academics",
        path: "/assignments",
    },
    // Assignments – Student
    {
        icon: <ListIcon />,
        name: "My Assignments",
        section: "Academics",
        path: "/assignments/my-assignments",
    },
    // Assignments – Parent (linked child)
    {
        icon: <ListIcon />,
        name: "My Child's Assignments",
        section: "Academics",
        path: "/parent/assignments",
    },
    // AI Homework Tracking (Teacher/Student/Admin)
    {
        icon: <TaskIcon />,
        name: "Homework AI",
        section: "Academics",
        path: "/homework",
    },
    // Exam Management (InstitutionAdmin, Principal)
    {
        icon: <PieChartIcon />,
        name: "Exam Management",
        section: "Academics",
        subItems: [
            { name: "Exams Type", path: "/exams", pro: false },
            { name: "Exam Timetable", path: "/exams/timetable", pro: false },
            { name: "Subject Configuration", path: "/exams/configs", pro: false },
            { name: "Seating Arrangement", path: "/exams/seating", pro: false },
        ],
    },
    // My Exam Timetable (Student)
    {
        icon: <PieChartIcon />,
        name: "My Exam Timetable",
        section: "Academics",
        path: "/exams/my-timetable",
    },
    // Exam timetable – Parent (linked child)
    {
        icon: <CalenderIcon />,
        name: "My Child's Exam Timetable",
        section: "Academics",
        path: "/parent/exam-timetable",
    },
    // My Invigilator Schedule (Teacher)
    {
        icon: <TaskIcon />,
        name: "My Invigilator Schedule",
        section: "Academics",
        path: "/exams/invigilator-schedule",
    },
    // Exam results – Student (own, published exams)
    {
        icon: <PieChartIcon />,
        name: "My Results",
        section: "Academics",
        path: "/academics/my-results",
    },
    // Exam results – Parent (linked child, published exams)
    {
        icon: <PieChartIcon />,
        name: "My Child's Results",
        section: "Academics",
        path: "/parent/results",
    },

    // ---------------- Attendance & Leave ----------------
    // Attendance (InstitutionAdmin, Principal, Teacher)
    {
        icon: <ListIcon />,
        name: "Attendance",
        section: "Attendance & Leave",
        subItems: [
            { name: "Mark Attendance", path: "/attendance/mark", pro: false },
            { name: "Attendance Report", path: "/attendance/report", pro: false },
            { name: "Staff Attendance", path: "/attendance/staff", pro: false },
            { name: "Staff Register", path: "/attendance/staff-register", pro: false },
        ],
    },
    // Attendance – Student (own)
    {
        icon: <CalenderIcon />,
        name: "My Attendance",
        section: "Attendance & Leave",
        path: "/attendance/my",
    },
    // Attendance – Parent (linked child)
    {
        icon: <CalenderIcon />,
        name: "My Child's Attendance",
        section: "Attendance & Leave",
        path: "/parent/attendance",
    },
    // Leave - approvers (class teachers, admins, "Approve leave" tick box)
    {
        icon: <TaskIcon />,
        name: "Leave Requests",
        section: "Attendance & Leave",
        path: "/leave/requests",
    },
    // Leave - students and staff apply for themselves
    {
        icon: <TaskIcon />,
        name: "My Leave",
        section: "Attendance & Leave",
        path: "/leave/my",
    },
    // Leave - Parent applies for the linked child
    {
        icon: <TaskIcon />,
        name: "My Child's Leave",
        section: "Attendance & Leave",
        path: "/leave/my",
    },
    // Calendar (holidays, weekly offs, exams, leave) - everyone in the institution
    {
        icon: <CalenderIcon />,
        name: "Calendar",
        section: "Attendance & Leave",
        path: "/calendar",
    },

    // ---------------- Communication ----------------
    // Announcements (InstitutionAdmin, Principal, Teacher, Student)
    {
        icon: <TableIcon />,
        name: "Announcements",
        section: "Communication",
        path: "/announcements",
    },

    // ---------------- Finance & Transport ----------------
    // Finance Management (InstitutionAdmin)
    {
        icon: <GridIcon />,
        name: "Finance Management",
        section: "Finance & Transport",
        subItems: [
            { name: "Fee Structure", path: "/finance/fee-structure", pro: false },
            { name: "Fee Collection", path: "/finance/fee-collection", pro: false },
            { name: "Fee Defaulters", path: "/finance/defaulters", pro: false },
            { name: "Collection Report", path: "/finance/collection-report", pro: false },
            { name: "Expenses", path: "/finance/expenses", pro: false },
            { name: "Salary Setup", path: "/finance/salary-setup", pro: false },
            { name: "Salary Payments", path: "/finance/salary-payments", pro: false },
        ],
    },
    // Fees – Parent (linked child)
    {
        icon: <GridIcon />,
        name: "My Child's Fees",
        section: "Finance & Transport",
        path: "/parent/fees",
    },
    // Bus Management (InstitutionAdmin, Principal, Bus Staff)
    {
        icon: <TaskIcon />,
        name: "Bus Management",
        section: "Finance & Transport",
        subItems: [
            { name: "Scan QR Code", path: "/bus-scan/scan", pro: false },
            { name: "Tracking Report", path: "/bus-scan/report", pro: false },
        ],
    },

    // ---------------- Administration ----------------
    // Institution Management (SuperAdmin Only)
    {
        icon: <BoxCubeIcon />,
        name: "Institution Management",
        section: "Administration",
        subItems: [
            { name: "List Institutions", path: "/institutions", pro: false },
            { name: "Create Institution", path: "/institutions/new", pro: false },
            { name: "Institution Admins", path: "/institution-admins", pro: false },
            { name: "System Admins", path: "/system-admins", pro: false },
        ],
    },
    // User Management (InstitutionAdmin, Principal)
    {
        icon: <UserCircleIcon />,
        name: "User Management",
        section: "Administration",
        subItems: [
            { name: "Users List", path: "/users", pro: false },
            { name: "Create User", path: "/users/new", pro: false },
            { name: "Teachers", path: "/teachers", pro: false },
            { name: "Students", path: "/students", pro: false },
            { name: "Parents", path: "/parents", pro: false },
            { name: "Roles & Permissions", path: "/roles", pro: false },
        ],
    },
];

const AppSidebar: React.FC = () => {
    const { isExpanded, isMobileOpen, isHovered, setIsHovered } = useSidebar();
    const location = useLocation();
    const { hasPermission, hasAnyPermission, isFullAccess, isSuperAdmin } = usePermissions();
    const userRole = useAuthStore((state) => state.user?.role);
    const features = useAuthStore((state) => state.user?.features); // switched on for the institution

    const [openSubmenuName, setOpenSubmenuName] = useState<string | null>(null);
    const [subMenuHeight, setSubMenuHeight] = useState<Record<string, number>>(
        {}
    );
    const subMenuRefs = useRef<Record<string, HTMLDivElement | null>>({});

    // const isActive = (path: string) => location.pathname === path;
    const isActive = useCallback(
        (path: string) =>
            location.pathname === path || location.pathname.startsWith(`${path}/`),
        [location.pathname]
    );

    useEffect(() => {
        let submenuMatched = false;
        allMenuItems.forEach((nav) => {
            if (nav.subItems) {
                nav.subItems.forEach((subItem) => {
                    const isCurrentOrChild =
                        location.pathname === subItem.path ||
                        location.pathname.startsWith(subItem.path + '/');
                    if (isCurrentOrChild) {
                        setOpenSubmenuName(nav.name);
                        submenuMatched = true;
                    }
                });
            }
        });

        if (!submenuMatched) {
            setOpenSubmenuName(null);
        }
    }, [location, isActive]);

    useEffect(() => {
        if (openSubmenuName !== null) {
            if (subMenuRefs.current[openSubmenuName]) {
                setSubMenuHeight((prevHeights) => ({
                    ...prevHeights,
                    [openSubmenuName]: subMenuRefs.current[openSubmenuName]?.scrollHeight || 0,
                }));
            }
        }
    }, [openSubmenuName]);

    const handleSubmenuToggle = (menuName: string) => {
        setOpenSubmenuName((prevName) => {
            if (prevName === menuName) {
                return null;
            }
            return menuName;
        });
    };

    // Permission-based menu filtering
    const filteredMenuItems = useMemo(() => {
        return allMenuItems.reduce<NavItem[]>((acc, nav) => {
            // Dashboard is always visible
            if (nav.name === "Dashboard") {
                acc.push(nav);
                return acc;
            }

            const sidebarConfig = SIDEBAR_PERMISSION_MAP[nav.name];

            // If no sidebar config exists, hide the item (safe default)
            if (!sidebarConfig) return acc;

            // Role-only items (e.g. a student's own attendance): shown to exactly those roles
            if (sidebarConfig.roles) {
                if (userRole && sidebarConfig.roles.includes(userRole)) acc.push(nav);
                return acc;
            }

            // SuperAdmin-only groups
            if (sidebarConfig.superAdminOnly) {
                if (isSuperAdmin) acc.push(nav);
                return acc;
            }

            // SuperAdmin only sees Dashboard + superAdmin-only groups (Institution Management)
            // All other groups are institution-specific and not relevant to SuperAdmin
            if (isSuperAdmin) return acc;

            // Full-access roles (INSTITUTION_ADMIN) see everything, except excluded paths
            if (isFullAccess) {
                const excluded = sidebarConfig.excludeFromFullAccess;
                if (excluded && excluded.length > 0) {
                    // Hide entire single-path item if its path is excluded
                    if (!nav.subItems && nav.path && excluded.includes(nav.path)) return acc;
                    // Filter sub-items
                    if (nav.subItems) {
                        const filtered = nav.subItems.filter((sub) => !excluded.includes(sub.path));
                        if (filtered.length === 0) return acc;
                        acc.push({ ...nav, subItems: filtered });
                        return acc;
                    }
                }
                acc.push(nav);
                return acc;
            }

            // Check if user has any of the group-level permissions
            if (!hasAnyPermission(sidebarConfig.groupPermissions)) return acc;

            // For single-path items (no sub-items), also check excludeIfHasPermission
            if (!nav.subItems) {
                if (isPathHiddenForRole(userRole, nav.path || '')) return acc;
                const excludePerm = sidebarConfig.excludeIfHasPermission?.[nav.path || ''];
                if (excludePerm && hasPermission(excludePerm)) return acc;
                acc.push(nav);
                return acc;
            }

            // Filter sub-items by individual item permissions
            const visibleSubItems = nav.subItems.filter((sub) => {
                if (isPathHiddenForRole(userRole, sub.path)) return false;
                const excludePerm = sidebarConfig.excludeIfHasPermission?.[sub.path];
                if (excludePerm && hasPermission(excludePerm)) return false;

                const requiredPerm = sidebarConfig.itemPermissions[sub.path];
                if (!requiredPerm) return true;
                return hasPermission(requiredPerm);
            });

            // Hide the entire group if no sub-items are visible
            if (visibleSubItems.length === 0) return acc;

            acc.push({ ...nav, subItems: visibleSubItems });

            return acc;
        }, []).reduce<NavItem[]>((acc, nav) => {
            // Features the Super Admin hasn't switched on for this institution (config/features.ts)
            if (!nav.subItems) {
                if (!isPageSwitchedOff(nav.path || '', features, userRole)) acc.push(nav);
                return acc;
            }
            const subItems = nav.subItems.filter((sub) => !isPageSwitchedOff(sub.path, features, userRole));
            if (subItems.length > 0) acc.push({ ...nav, subItems });
            return acc;
        }, []);
    }, [isFullAccess, isSuperAdmin, hasPermission, hasAnyPermission, userRole, features]);

    // Visible items grouped under their headings (items with no section come first, no heading)
    const menuSections = useMemo(() => {
        const groups = [undefined, ...SECTION_ORDER].map((title) => ({
            title,
            items: filteredMenuItems.filter((nav) => nav.section === title),
        }));
        return groups.filter((group) => group.items.length > 0);
    }, [filteredMenuItems]);

    const renderMenuItems = (items: NavItem[]) => (
        <ul className="flex flex-col gap-4">
            {items.map((nav) => (
                <li key={nav.name}>
                    {nav.subItems ? (
                        <button
                            onClick={() => handleSubmenuToggle(nav.name)}
                            className={`menu-item group ${openSubmenuName === nav.name
                                ? "menu-item-active"
                                : "menu-item-inactive"
                                } cursor-pointer ${!isExpanded && !isHovered
                                    ? "lg:justify-center"
                                    : "lg:justify-start"
                                }`}
                        >
                            <span
                                className={`menu-item-icon-size  ${openSubmenuName === nav.name
                                    ? "menu-item-icon-active"
                                    : "menu-item-icon-inactive"
                                    }`}
                            >
                                {nav.icon}
                            </span>
                            {(isExpanded || isHovered || isMobileOpen) && (
                                <span className="menu-item-text">{nav.name}</span>
                            )}
                            {(isExpanded || isHovered || isMobileOpen) && (
                                <ChevronDownIcon
                                    className={`ml-auto w-5 h-5 transition-transform duration-200 ${openSubmenuName === nav.name
                                        ? "rotate-180 text-brand-500"
                                        : ""
                                        }`}
                                />
                            )}
                        </button>
                    ) : (
                        nav.path && (
                            <Link
                                to={nav.path}
                                className={`menu-item group ${isActive(nav.path) ? "menu-item-active" : "menu-item-inactive"
                                    }`}
                            >
                                <span
                                    className={`menu-item-icon-size ${isActive(nav.path)
                                        ? "menu-item-icon-active"
                                        : "menu-item-icon-inactive"
                                        }`}
                                >
                                    {nav.icon}
                                </span>
                                {(isExpanded || isHovered || isMobileOpen) && (
                                    <span className="menu-item-text">{nav.name}</span>
                                )}
                            </Link>
                        )
                    )}
                    {nav.subItems && (isExpanded || isHovered || isMobileOpen) && (
                        <div
                            ref={(el) => {
                                subMenuRefs.current[nav.name] = el;
                            }}
                            className="overflow-hidden transition-all duration-300"
                            style={{
                                height:
                                    openSubmenuName === nav.name
                                        ? `${subMenuHeight[nav.name]}px`
                                        : "0px",
                            }}
                        >
                            <ul className="mt-2 space-y-1 ml-9">
                                {nav.subItems.map((subItem) => (
                                    <li key={subItem.name}>
                                        <Link
                                            to={subItem.path}
                                            className={`menu-dropdown-item ${isActive(subItem.path)
                                                ? "menu-dropdown-item-active"
                                                : "menu-dropdown-item-inactive"
                                                }`}
                                        >
                                            {subItem.name}
                                            <span className="flex items-center gap-1 ml-auto">
                                                {subItem.new && (
                                                    <span
                                                        className={`ml-auto ${isActive(subItem.path)
                                                            ? "menu-dropdown-badge-active"
                                                            : "menu-dropdown-badge-inactive"
                                                            } menu-dropdown-badge`}
                                                    >
                                                        new
                                                    </span>
                                                )}
                                                {subItem.pro && (
                                                    <span
                                                        className={`ml-auto ${isActive(subItem.path)
                                                            ? "menu-dropdown-badge-active"
                                                            : "menu-dropdown-badge-inactive"
                                                            } menu-dropdown-badge`}
                                                    >
                                                        pro
                                                    </span>
                                                )}
                                            </span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </li>
            ))}
        </ul>
    );

    return (
        <aside
            className={`fixed mt-16 flex flex-col lg:mt-0 top-0 px-5 left-0 bg-white dark:bg-gray-900 dark:border-gray-800 text-gray-900 h-screen transition-all duration-300 ease-in-out z-50 border-r border-gray-200 
        ${isExpanded || isMobileOpen
                    ? "w-[290px]"
                    : isHovered
                        ? "w-[290px]"
                        : "w-[90px]"
                }
        ${isMobileOpen ? "translate-x-0" : "-translate-x-full"}
        lg:translate-x-0`}
            onMouseEnter={() => !isExpanded && setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <div
                className="py-5 flex justify-center"
            >
                <Link to="/dashboard">
                    {isExpanded || isHovered || isMobileOpen ? (
                        <>
                            <img
                                className="h-[37px] w-auto dark:hidden"
                                src="/images/logo/eduspyre/eduspyre-logo-light.png"
                                alt="EduSpyre"
                                width={135}
                                height={37}
                            />
                            <img
                                className="hidden h-[37px] w-auto dark:block"
                                src="/images/logo/eduspyre/eduspyre-logo-dark.png"
                                alt="EduSpyre"
                                width={135}
                                height={37}
                            />
                        </>
                    ) : (
                        <img
                            src="/images/logo/eduspyre/eduspyre-icon.png"
                            alt="EduSpyre"
                            width={40}
                            height={40}
                        />
                    )}
                </Link>
            </div>
            <div className="flex flex-col overflow-y-auto duration-300 ease-linear no-scrollbar">
                <nav className="mb-6 flex flex-col gap-6">
                    {menuSections.map((group) => (
                        <div key={group.title ?? "top"}>
                            {group.title &&
                                (isExpanded || isHovered || isMobileOpen ? (
                                    <h2 className="mb-3 px-3 text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                                        {group.title}
                                    </h2>
                                ) : (
                                    // Icons-only sidebar: a line marks where a section starts
                                    <div
                                        className="mb-4 border-t border-gray-200 dark:border-gray-800"
                                        role="separator"
                                        aria-label={group.title}
                                    />
                                ))}
                            {renderMenuItems(group.items)}
                        </div>
                    ))}
                </nav>
                {/* {isExpanded || isHovered || isMobileOpen ? <SidebarWidget /> : null} */}
            </div>
        </aside>
    );
};

export default AppSidebar;

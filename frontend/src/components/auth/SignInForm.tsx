import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router";
import toast from "react-hot-toast";
import { EyeCloseIcon, EyeIcon } from "../../icons";
import { useAuth } from "../../hooks/useAuth";
import { CONTACT } from "../../config/contact";
import AuthMobileLogo from "./AuthMobileLogo";
import { AlertCircleIcon, ArrowRightIcon, LockIcon, MailIcon } from "../common/StrokeIcons";

const inputBase =
    "h-12 short:h-11 w-full rounded-xl border bg-white pl-11 text-sm text-gray-900 shadow-theme-xs transition placeholder:text-gray-400 focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gray-900 dark:text-white dark:placeholder:text-gray-500";
const inputOk =
    "border-gray-300 focus:border-brand-400 focus:ring-brand-500/15 dark:border-gray-700 dark:focus:border-brand-500";
const inputError =
    "border-error-300 focus:border-error-400 focus:ring-error-500/15 dark:border-error-500/50";
const fieldIcon =
    "pointer-events-none absolute left-4 top-1/2 size-[18px] -translate-y-1/2 text-gray-400 dark:text-gray-500";

export default function SignInForm() {
    const [showPassword, setShowPassword] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [capsLockOn, setCapsLockOn] = useState(false);
    const emailRef = useRef<HTMLInputElement>(null);
    const navigate = useNavigate();
    const { login } = useAuth();

    // Focus the email field only with a mouse/trackpad: on touch screens it would
    // pop the keyboard up on load and push the form out of view.
    useEffect(() => {
        if (window.matchMedia?.("(pointer: fine)").matches) emailRef.current?.focus();
    }, []);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!email || !password) {
            setError("Please enter your email and password.");
            return;
        }

        setIsLoading(true);
        try {
            await login({ identifier: email, password });
            toast.success("Login successful!");
            navigate("/dashboard");
        } catch (err) {
            const { status, message } = (err ?? {}) as { status?: number; message?: string };
            // The login endpoint is rate limited (5/min per IP) and its 429 has no readable message.
            setError(
                status === 429
                    ? "Too many sign-in attempts. Please wait a minute and try again."
                    : message || "Login failed. Please try again.",
            );
        } finally {
            setIsLoading(false);
        }
    };

    const trackCapsLock = (e: KeyboardEvent<HTMLInputElement>) => {
        setCapsLockOn(e.getModifierState("CapsLock"));
    };

    const inputState = error ? inputError : inputOk;

    return (
        <div className="auth-rise flex flex-1 items-center justify-center px-5 py-4 short:py-2 sm:px-10 sm:py-8">
            <div className="w-full max-w-[400px]">
                <AuthMobileLogo />

                <div className="mb-6 text-center short:mb-4 sm:mb-8 lg:text-left">
                    <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl dark:text-white">Welcome back</h1>
                    <p className="mt-1.5 text-sm leading-relaxed text-gray-500 very-short:hidden sm:mt-2 dark:text-gray-400">
                        Sign in with the email and password provided by your school.
                    </p>
                </div>

                {error && (
                    <div
                        role="alert"
                        className="mb-5 flex items-start gap-3 short:mb-3 short:py-2 very-short:mb-2 sm:mb-6 rounded-xl border border-error-200 bg-error-50 px-4 py-3 text-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
                    >
                        <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
                        <span>{error}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4 short:space-y-3 very-short:space-y-2.5 sm:space-y-5">
                    <div>
                        <label htmlFor="signin-email" className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Email
                        </label>
                        <div className="relative">
                            <MailIcon className={fieldIcon} />
                            <input
                                id="signin-email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                ref={emailRef}
                                required
                                placeholder="you@school.edu"
                                value={email}
                                onChange={(e) => {
                                    setEmail(e.target.value);
                                    if (error) setError(null);
                                }}
                                disabled={isLoading}
                                aria-invalid={!!error}
                                className={`${inputBase} ${inputState} pr-4`}
                            />
                        </div>
                    </div>

                    <div>
                        <div className="mb-2 flex items-center justify-between">
                            <label htmlFor="signin-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                Password
                            </label>
                            <Link
                                to="/forgot-password"
                                className="text-sm font-medium text-brand-500 transition-colors hover:text-brand-600 dark:text-brand-400 dark:hover:text-brand-300"
                            >
                                Forgot password?
                            </Link>
                        </div>
                        <div className="relative">
                            <LockIcon className={fieldIcon} />
                            <input
                                id="signin-password"
                                name="password"
                                type={showPassword ? "text" : "password"}
                                autoComplete="current-password"
                                required
                                placeholder="Enter your password"
                                value={password}
                                onChange={(e) => {
                                    setPassword(e.target.value);
                                    if (error) setError(null);
                                }}
                                onKeyDown={trackCapsLock}
                                onKeyUp={trackCapsLock}
                                onBlur={() => setCapsLockOn(false)}
                                disabled={isLoading}
                                aria-invalid={!!error}
                                aria-describedby={capsLockOn ? "signin-capslock" : undefined}
                                className={`${inputBase} ${inputState} pr-12`}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword((v) => !v)}
                                aria-label={showPassword ? "Hide password" : "Show password"}
                                aria-pressed={showPassword}
                                className="absolute right-1.5 top-1/2 flex size-9 -translate-y-1/2 items-center justify-center rounded-lg transition hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/20 dark:hover:bg-white/5"
                            >
                                {showPassword ? (
                                    <EyeIcon className="size-5 fill-gray-500 dark:fill-gray-400" />
                                ) : (
                                    <EyeCloseIcon className="size-5 fill-gray-500 dark:fill-gray-400" />
                                )}
                            </button>
                        </div>
                        {capsLockOn && (
                            <p id="signin-capslock" className="mt-2 text-xs font-medium text-warning-600 dark:text-warning-400">
                                Caps Lock is on
                            </p>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="group mt-6 flex short:mt-4 sm:mt-7 h-12 short:h-11 w-full items-center justify-center gap-2 rounded-xl bg-brand-500 text-sm font-semibold text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-600 hover:shadow-brand-500/35 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 disabled:cursor-not-allowed disabled:opacity-75"
                    >
                        {isLoading ? (
                            <>
                                <span
                                    aria-hidden="true"
                                    className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                                />
                                Signing in…
                            </>
                        ) : (
                            <>
                                Sign in
                                <ArrowRightIcon className="size-4 transition-transform group-hover:translate-x-0.5" />
                            </>
                        )}
                    </button>
                </form>

                <div className="mt-6 rounded-2xl border border-gray-200 bg-gray-50/80 px-4 py-3 text-center text-sm short:mt-4 short:py-2.5 very-short:mt-3 very-short:py-2 sm:mt-8 sm:px-5 sm:py-4 lg:text-left leading-relaxed text-gray-600 dark:border-white/10 dark:bg-white/[0.03] dark:text-gray-400">
                    <p>No account? Ask your school administrator.</p>
                    <p className="mt-1">
                        New to EduSpyre?{" "}
                        <a
                            href={CONTACT.demoUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-semibold text-brand-500 transition-colors hover:text-brand-600 dark:text-brand-400 dark:hover:text-brand-300"
                        >
                            Book a demo
                            <span className="sr-only"> (opens in a new tab)</span>
                        </a>
                    </p>
                </div>
            </div>
        </div>
    );
}

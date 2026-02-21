import { redirect } from "next/navigation";

// /onboarding has no content of its own — always go straight to institute selection.
export default function OnboardingIndexPage() {
    redirect("/onboarding/institute");
}

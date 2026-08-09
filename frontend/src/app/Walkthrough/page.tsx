import { redirect } from "next/navigation";

// Preserve the previously shared URL while moving visitors to the real home page.
export default function WalkthroughPage() {
  redirect("/");
}

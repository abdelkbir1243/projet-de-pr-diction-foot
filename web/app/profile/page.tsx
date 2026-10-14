import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/primitives";
import { ProfileView } from "@/components/profile-view";
import { getMatches, summarize, teamLite } from "@/lib/data";

export const metadata: Metadata = { title: "Profil et favoris", robots: { index: false } };

export default function ProfilePage() {
  const m = getMatches();
  return (
    <>
      <PageHeader eyebrow="Espace personnel" title="Profil" subtitle="Vos équipes et matchs favoris, vos préférences d'affichage." />
      <ProfileView teams={teamLite()} matches={m.map(summarize)} />
    </>
  );
}

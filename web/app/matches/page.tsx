import type { Metadata } from "next";
import { HomeView } from "../home-view";

export const metadata: Metadata = { title: "Matchs du jour", alternates: { canonical: "/matches" } };
export default function MatchesPage() {
  return <HomeView />;
}

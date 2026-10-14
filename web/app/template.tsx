/* Transition d'entrée discrète à chaque navigation (le template est remonté à chaque changement de page). */
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="animate-page">{children}</div>;
}

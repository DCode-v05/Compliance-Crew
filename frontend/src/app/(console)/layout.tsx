import TopNav from "@/components/TopNav";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <TopNav />
      <main className="mx-auto max-w-[1180px] px-7 py-9">{children}</main>
    </div>
  );
}

import Link from 'next/link';

export default function Header() {
  return (
    <header className="border-b border-midnight/30 bg-deep/30 backdrop-blur-md sticky top-0 z-50 fade-in">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link href="/" className="group">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-aurora-teal via-aurora-green to-aurora-purple bg-clip-text text-transparent group-hover:scale-105 transition-transform duration-300">
              ◈ JobQuest
            </h1>
            <p className="text-xs text-frost/50 tracking-widest uppercase">Find Your Perfect Role</p>
          </Link>

          <nav className="flex gap-6">
            <Link
              href="/"
              className="text-frost/70 hover:text-aurora-teal transition-colors duration-300 font-semibold"
            >
              Jobs
            </Link>
            <Link
              href="/companies"
              className="text-frost/70 hover:text-aurora-purple transition-colors duration-300 font-semibold"
            >
              Companies
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}

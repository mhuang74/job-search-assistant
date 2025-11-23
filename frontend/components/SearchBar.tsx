'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/?q=${encodeURIComponent(query)}`);
    } else {
      router.push('/');
    }
  };

  return (
    <form onSubmit={handleSearch} className="w-full max-w-3xl mx-auto mb-8 slide-up">
      <div className="relative group">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search jobs by title, company, or description..."
          className="w-full px-6 py-4 bg-deep/50 backdrop-blur-sm border-2 border-midnight/50 rounded-lg text-frost placeholder-frost/40 focus:outline-none focus:border-aurora-teal/50 focus:ring-2 focus:ring-aurora-teal/20 transition-all duration-300 card-glow"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2 bg-gradient-to-r from-aurora-teal to-aurora-green text-void font-bold rounded-md hover:shadow-lg hover:shadow-aurora-teal/50 transition-all duration-300 hover:scale-105"
        >
          Search
        </button>
      </div>
    </form>
  );
}

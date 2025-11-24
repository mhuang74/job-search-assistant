'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Company, TeamMember } from '@/lib/db';

interface CompanyData extends Company {
  teamMembers: TeamMember[];
  countries: string[];
}

export default function EmployeesPage() {
  const params = useParams();
  const [company, setCompany] = useState<CompanyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCountry, setSelectedCountry] = useState<string>('all');

  useEffect(() => {
    async function fetchCompany() {
      try {
        const res = await fetch(`/api/companies/${params.id}`);
        if (res.ok) {
          const data = await res.json();
          setCompany(data);
        }
      } catch (error) {
        console.error('Error fetching company:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchCompany();
  }, [params.id]);

  if (loading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-20">
          <div className="shimmer w-32 h-32 mx-auto mb-4 rounded-lg bg-midnight/50"></div>
          <p className="text-frost/50">Loading employees...</p>
        </div>
      </div>
    );
  }

  if (!company) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-20">
          <div className="text-6xl mb-4">👥</div>
          <h3 className="text-2xl font-bold text-frost/70 mb-2">Company not found</h3>
          <Link href="/companies" className="text-aurora-teal hover:glow-teal">
            ← Back to companies
          </Link>
        </div>
      </div>
    );
  }

  const filteredMembers =
    selectedCountry === 'all'
      ? company.teamMembers
      : company.teamMembers.filter((m) => m.country === selectedCountry);

  // Group by country for better organization
  const membersByCountry = filteredMembers.reduce((acc, member) => {
    const country = member.country || 'Unknown';
    if (!acc[country]) {
      acc[country] = [];
    }
    acc[country].push(member);
    return acc;
  }, {} as Record<string, TeamMember[]>);

  return (
    <div className="container mx-auto px-6 py-8 max-w-6xl">
      <div className="fade-in">
        {/* Back button */}
        <Link
          href={`/companies/${params.id}`}
          className="inline-flex items-center gap-2 text-aurora-purple hover:glow-purple mb-6 transition-all"
        >
          ← Back to {company.name}
        </Link>

        {/* Header */}
        <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 mb-6">
          <h1 className="text-4xl font-bold text-aurora-teal mb-4 glow-teal">
            Team Members at {company.name}
          </h1>
          <p className="text-frost/70 text-lg mb-4">
            {filteredMembers.length} {selectedCountry !== 'all' ? `in ${selectedCountry}` : 'total'}
          </p>

          {/* Country filter */}
          {company.countries && company.countries.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setSelectedCountry('all')}
                className={`px-4 py-2 rounded-lg transition-all ${
                  selectedCountry === 'all'
                    ? 'bg-aurora-teal text-void font-bold'
                    : 'bg-midnight/50 text-frost/70 hover:bg-midnight'
                }`}
              >
                All ({company.teamMembers.length})
              </button>
              {company.countries.map((country) => {
                const count = company.teamMembers.filter((m) => m.country === country).length;
                return (
                  <button
                    key={country}
                    onClick={() => setSelectedCountry(country)}
                    className={`px-4 py-2 rounded-lg transition-all ${
                      selectedCountry === country
                        ? 'bg-aurora-teal text-void font-bold'
                        : 'bg-midnight/50 text-frost/70 hover:bg-midnight'
                    }`}
                  >
                    {country} ({count})
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Members grouped by country */}
        {selectedCountry === 'all' ? (
          <div className="space-y-8">
            {Object.entries(membersByCountry)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([country, members], idx) => {
                const staggerClass = idx < 5 ? `stagger-${idx + 1}` : '';
                return (
                  <div
                    key={country}
                    className={`card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 slide-up ${staggerClass}`}
                  >
                    <h2 className="text-2xl font-bold text-aurora-purple mb-4">
                      {country} ({members.length})
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {members.map((member) => (
                        <Link
                          key={member.id}
                          href={`/employees/${member.id}`}
                          className="p-4 bg-midnight/30 rounded-lg hover:bg-midnight/50 transition-all group"
                        >
                          <h3 className="font-bold text-frost group-hover:text-aurora-teal transition-colors">
                            {member.name}
                          </h3>
                          {member.title && (
                            <p className="text-sm text-frost/70 mb-2 line-clamp-2">{member.title}</p>
                          )}
                          {member.city && (
                            <p className="text-xs text-frost/50">{member.city}</p>
                          )}
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
          </div>
        ) : (
          <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 slide-up">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredMembers.map((member, idx) => {
                const staggerClass = idx < 5 ? `stagger-${idx + 1}` : '';
                return (
                  <Link
                    key={member.id}
                    href={`/employees/${member.id}`}
                    className={`p-4 bg-midnight/30 rounded-lg hover:bg-midnight/50 transition-all group slide-up ${staggerClass}`}
                  >
                    <h3 className="font-bold text-frost group-hover:text-aurora-teal transition-colors">
                      {member.name}
                    </h3>
                    {member.title && (
                      <p className="text-sm text-frost/70 mb-2 line-clamp-2">{member.title}</p>
                    )}
                    {member.city && (
                      <p className="text-xs text-frost/50">{member.city}</p>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {filteredMembers.length === 0 && (
          <div className="text-center py-20 slide-up">
            <div className="text-6xl mb-4">👥</div>
            <h3 className="text-2xl font-bold text-frost/70 mb-2">No team members found</h3>
            <p className="text-frost/50">Try selecting a different country filter</p>
          </div>
        )}
      </div>
    </div>
  );
}

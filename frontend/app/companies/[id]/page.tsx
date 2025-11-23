'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Company, Job, TeamMember } from '@/lib/db';

interface CompanyData extends Company {
  jobs: Job[];
  teamMembers: TeamMember[];
  countries: string[];
}

export default function CompanyPage() {
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
          <p className="text-frost/50">Loading company details...</p>
        </div>
      </div>
    );
  }

  if (!company) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-20">
          <div className="text-6xl mb-4">🏢</div>
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

  return (
    <div className="container mx-auto px-6 py-8 max-w-6xl">
      <div className="fade-in">
        {/* Back button */}
        <Link
          href="/companies"
          className="inline-flex items-center gap-2 text-aurora-purple hover:glow-purple mb-6 transition-all"
        >
          ← Back to companies
        </Link>

        {/* Company header */}
        <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 mb-6">
          <h1 className="text-4xl font-bold text-aurora-purple mb-4 glow-purple">
            {company.name}
          </h1>

          {company.description && (
            <p className="text-frost/80 text-lg mb-6">{company.description}</p>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {company.industry && (
              <div>
                <div className="text-frost/50 text-sm mb-1">Industry</div>
                <div className="text-frost font-semibold">{company.industry}</div>
              </div>
            )}
            {company.headquarters_location && (
              <div>
                <div className="text-frost/50 text-sm mb-1">Headquarters</div>
                <div className="text-frost font-semibold">{company.headquarters_location}</div>
              </div>
            )}
            {company.company_size && (
              <div>
                <div className="text-frost/50 text-sm mb-1">Company Size</div>
                <div className="text-frost font-semibold">{company.company_size}</div>
              </div>
            )}
            {company.taiwan_employee_count && (
              <div>
                <div className="text-frost/50 text-sm mb-1">Asia Team</div>
                <div className="text-aurora-teal font-semibold">
                  {company.taiwan_employee_count} {company.taiwan_employee_count === 1 ? 'member' : 'members'}
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-4">
            {company.linkedin_url && (
              <a
                href={company.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-gradient-to-r from-aurora-purple to-aurora-pink text-void font-bold rounded-lg hover:shadow-lg hover:shadow-aurora-purple/50 transition-all duration-300 hover:scale-105"
              >
                View on LinkedIn →
              </a>
            )}
            {company.website && (
              <a
                href={company.website}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-midnight/50 text-frost border border-midnight rounded-lg hover:bg-midnight transition-all"
              >
                Company Website →
              </a>
            )}
          </div>
        </div>

        {/* Open positions */}
        {company.jobs && company.jobs.length > 0 && (
          <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 mb-6 slide-up stagger-1">
            <h2 className="text-2xl font-bold text-frost mb-4">
              Open Positions ({company.jobs.length})
            </h2>
            <div className="space-y-4">
              {company.jobs.map((job) => (
                <Link
                  key={job.id}
                  href={`/jobs/${job.id}`}
                  className="block p-4 bg-midnight/30 rounded-lg hover:bg-midnight/50 transition-all group"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-bold text-aurora-teal group-hover:glow-teal transition-all">
                        {job.title}
                      </h3>
                      <div className="flex items-center gap-3 text-sm text-frost/70 mt-1">
                        <span>{job.location}</span>
                        {job.remote_type && (
                          <>
                            <span>•</span>
                            <span className="text-aurora-green">{job.remote_type}</span>
                          </>
                        )}
                        {job.job_type && (
                          <>
                            <span>•</span>
                            <span>{job.job_type}</span>
                          </>
                        )}
                      </div>
                    </div>
                    {job.ranking_score && job.ranking_score > 0 && (
                      <div className="text-shimmer font-bold glow-pink">
                        {job.ranking_score.toFixed(1)}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Team members */}
        {company.teamMembers && company.teamMembers.length > 0 && (
          <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 slide-up stagger-2">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-frost">
                <Link
                  href={`/companies/${company.id}/employees`}
                  className="hover:text-aurora-teal transition-colors"
                >
                  Team Members ({filteredMembers.length})
                </Link>
              </h2>

              {/* Country filter */}
              {company.countries && company.countries.length > 1 && (
                <select
                  value={selectedCountry}
                  onChange={(e) => setSelectedCountry(e.target.value)}
                  className="px-4 py-2 bg-midnight/50 border border-midnight rounded-lg text-frost focus:outline-none focus:border-aurora-teal/50 focus:ring-2 focus:ring-aurora-teal/20 transition-all"
                >
                  <option value="all">All Countries ({company.teamMembers.length})</option>
                  {company.countries.map((country) => {
                    const count = company.teamMembers.filter((m) => m.country === country).length;
                    return (
                      <option key={country} value={country}>
                        {country} ({count})
                      </option>
                    );
                  })}
                </select>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredMembers.slice(0, 12).map((member) => (
                <Link
                  key={member.id}
                  href={`/employees/${member.id}`}
                  className="p-4 bg-midnight/30 rounded-lg hover:bg-midnight/50 transition-all group"
                >
                  <h3 className="font-bold text-frost group-hover:text-aurora-teal transition-colors">
                    {member.name}
                  </h3>
                  {member.title && (
                    <p className="text-sm text-frost/70 mb-2">{member.title}</p>
                  )}
                  <div className="flex items-center gap-2 text-xs text-frost/50">
                    {member.city && <span>{member.city}</span>}
                    {member.city && member.country && <span>•</span>}
                    {member.country && <span>{member.country}</span>}
                  </div>
                </Link>
              ))}
            </div>

            {filteredMembers.length > 12 && (
              <div className="mt-6 text-center">
                <Link
                  href={`/companies/${company.id}/employees`}
                  className="inline-block px-6 py-3 bg-aurora-teal/20 text-aurora-teal border border-aurora-teal/30 rounded-lg hover:bg-aurora-teal/30 transition-all"
                >
                  View all {filteredMembers.length} team members →
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

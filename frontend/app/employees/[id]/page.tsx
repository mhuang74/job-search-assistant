'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { TeamMember, Company } from '@/lib/db';

interface EmployeeData extends TeamMember {
  company?: Company;
}

export default function EmployeePage() {
  const params = useParams();
  const [employee, setEmployee] = useState<EmployeeData | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEmployee() {
      try {
        const res = await fetch(`/api/employees/${params.id}`);
        if (res.ok) {
          const employeeData = await res.json();
          setEmployee(employeeData);

          // Fetch company data
          if (employeeData.company_id) {
            const companyRes = await fetch(`/api/companies/${employeeData.company_id}`);
            if (companyRes.ok) {
              const companyData = await companyRes.json();
              setCompany(companyData);
            }
          }
        }
      } catch (error) {
        console.error('Error fetching employee:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchEmployee();
  }, [params.id]);

  if (loading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-20">
          <div className="shimmer w-32 h-32 mx-auto mb-4 rounded-full bg-midnight/50"></div>
          <p className="text-frost/50">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-20">
          <div className="text-6xl mb-4">👤</div>
          <h3 className="text-2xl font-bold text-frost/70 mb-2">Employee not found</h3>
          <Link href="/companies" className="text-aurora-teal hover:glow-teal">
            ← Back to companies
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      <div className="fade-in">
        {/* Back button */}
        {company && (
          <Link
            href={`/companies/${company.id}/employees`}
            className="inline-flex items-center gap-2 text-aurora-purple hover:glow-purple mb-6 transition-all"
          >
            ← Back to {company.name} team
          </Link>
        )}

        {/* Employee profile card */}
        <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 mb-6">
          <div className="flex items-start gap-6">
            {/* Avatar placeholder */}
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-aurora-teal to-aurora-purple flex items-center justify-center text-4xl font-bold text-void">
              {employee.name.charAt(0).toUpperCase()}
            </div>

            <div className="flex-1">
              <h1 className="text-4xl font-bold text-aurora-teal mb-2 glow-teal">
                {employee.name}
              </h1>

              {employee.title && (
                <p className="text-xl text-frost/80 mb-4">{employee.title}</p>
              )}

              <div className="flex flex-wrap gap-3 mb-6">
                {employee.location && (
                  <span className="bg-midnight/50 text-frost/70 px-4 py-2 rounded-full border border-midnight flex items-center gap-2">
                    📍 {employee.location}
                  </span>
                )}
                {employee.city && (
                  <span className="bg-aurora-purple/20 text-aurora-purple px-4 py-2 rounded-full border border-aurora-purple/30">
                    {employee.city}
                  </span>
                )}
                {employee.country && (
                  <span className="bg-aurora-teal/20 text-aurora-teal px-4 py-2 rounded-full border border-aurora-teal/30">
                    {employee.country}
                  </span>
                )}
              </div>

              {employee.linkedin_url && (
                <a
                  href={employee.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block px-8 py-3 bg-gradient-to-r from-aurora-teal to-aurora-green text-void font-bold rounded-lg hover:shadow-lg hover:shadow-aurora-teal/50 transition-all duration-300 hover:scale-105"
                >
                  View LinkedIn Profile →
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Company information */}
        {company && (
          <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 mb-6 slide-up stagger-1">
            <h2 className="text-2xl font-bold text-frost mb-4">Company</h2>

            <div className="flex justify-between items-start">
              <div>
                <Link
                  href={`/companies/${company.id}`}
                  className="text-2xl font-bold text-aurora-purple hover:glow-purple mb-2 inline-block transition-all"
                >
                  {company.name}
                </Link>

                {company.description && (
                  <p className="text-frost/70 mb-4 mt-2">{company.description}</p>
                )}

                <div className="grid grid-cols-2 gap-4">
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
              </div>
            </div>

            <div className="flex gap-4 mt-6">
              <Link
                href={`/companies/${company.id}`}
                className="px-6 py-2 bg-aurora-purple/20 text-aurora-purple border border-aurora-purple/30 rounded-lg hover:bg-aurora-purple/30 transition-all"
              >
                View Company Profile
              </Link>
              {company.linkedin_url && (
                <a
                  href={company.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-6 py-2 bg-midnight/50 text-frost border border-midnight rounded-lg hover:bg-midnight transition-all"
                >
                  Company LinkedIn →
                </a>
              )}
            </div>
          </div>
        )}

        {/* Additional information placeholder */}
        <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 slide-up stagger-2">
          <h2 className="text-2xl font-bold text-frost mb-4">About</h2>
          <p className="text-frost/70">
            {employee.name} is a {employee.title || 'professional'} at{' '}
            {company ? (
              <Link href={`/companies/${company.id}`} className="text-aurora-purple hover:glow-purple">
                {company.name}
              </Link>
            ) : (
              'their company'
            )}
            {employee.city && `, based in ${employee.city}`}
            {employee.country && `, ${employee.country}`}.
          </p>
          {employee.linkedin_url && (
            <p className="text-frost/50 mt-4 text-sm">
              For more information about their professional background, visit their LinkedIn profile.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

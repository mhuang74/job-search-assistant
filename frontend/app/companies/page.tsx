import { getCompanies } from '@/lib/db';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function CompaniesPage() {
  const companies = getCompanies(100);

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="text-center mb-12 fade-in">
        <h2 className="text-5xl font-bold mb-4 bg-gradient-to-r from-aurora-purple via-aurora-pink to-aurora-teal bg-clip-text text-transparent">
          Explore Companies
        </h2>
        <p className="text-frost/60 text-lg">
          {companies.length} companies with Asia team presence
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {companies.map((company, index) => {
          const staggerClass = index < 5 ? `stagger-${index + 1}` : '';
          return (
            <Link
              key={company.id}
              href={`/companies/${company.id}`}
              className={`card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-6 slide-up ${staggerClass} group hover:scale-[1.02] transition-all duration-300`}
            >
              <h3 className="text-2xl font-bold text-aurora-purple mb-3 group-hover:glow-purple transition-all">
                {company.name}
              </h3>

              {company.description && (
                <p className="text-frost/70 text-sm mb-4 line-clamp-3">
                  {company.description}
                </p>
              )}

              <div className="space-y-2 mb-4">
                {company.industry && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-frost/50">Industry:</span>
                    <span className="text-aurora-teal">{company.industry}</span>
                  </div>
                )}
                {company.headquarters_location && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-frost/50">HQ:</span>
                    <span className="text-frost/80">{company.headquarters_location}</span>
                  </div>
                )}
              </div>

              <div className="flex gap-2 flex-wrap">
                {company.taiwan_employee_count && company.taiwan_employee_count > 0 && (
                  <span className="bg-aurora-teal/20 text-aurora-teal px-3 py-1 rounded-full border border-aurora-teal/30 text-xs font-semibold">
                    {company.taiwan_employee_count} Asia {company.taiwan_employee_count === 1 ? 'member' : 'members'}
                  </span>
                )}
                {company.company_size && (
                  <span className="bg-midnight/50 text-frost/70 px-3 py-1 rounded-full border border-midnight text-xs">
                    {company.company_size}
                  </span>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {companies.length === 0 && (
        <div className="text-center py-20 slide-up">
          <div className="text-6xl mb-4">🏢</div>
          <h3 className="text-2xl font-bold text-frost/70 mb-2">No companies found</h3>
          <p className="text-frost/50">Check back later for updates</p>
        </div>
      )}
    </div>
  );
}

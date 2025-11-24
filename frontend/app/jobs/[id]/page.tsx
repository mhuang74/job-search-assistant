import { getJobById, getCompanyById } from '@/lib/db';
import Link from 'next/link';
import { notFound } from 'next/navigation';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function JobPage({ params }: PageProps) {
  const { id } = await params;
  const job = getJobById(id);

  if (!job) {
    notFound();
  }

  const company = job.company_id ? getCompanyById(job.company_id) : null;

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      <div className="fade-in">
        {/* Back button */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-aurora-teal hover:glow-teal mb-6 transition-all"
        >
          ← Back to jobs
        </Link>

        {/* Job header */}
        <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 mb-6">
          <h1 className="text-4xl font-bold text-aurora-teal mb-4 glow-teal">
            {job.title}
          </h1>

          <div className="flex flex-wrap items-center gap-4 text-lg mb-6">
            {job.company_id && company ? (
              <Link
                href={`/companies/${job.company_id}`}
                className="text-aurora-purple hover:glow-purple font-bold transition-all"
              >
                {job.company}
              </Link>
            ) : (
              <span className="text-aurora-purple font-bold">{job.company}</span>
            )}
            <span className="text-frost/50">•</span>
            <span className="text-frost/80">{job.location}</span>
            {job.remote_type && (
              <>
                <span className="text-frost/50">•</span>
                <span className="text-aurora-green">{job.remote_type}</span>
              </>
            )}
          </div>

          {/* Tags */}
          <div className="flex flex-wrap gap-3 mb-6">
            {job.ranking_score && job.ranking_score > 0 && (
              <span className="bg-shimmer/20 text-shimmer px-4 py-2 rounded-full border border-shimmer/30 font-bold">
                ⭐ Score: {job.ranking_score.toFixed(1)}
              </span>
            )}
            {job.taiwan_team_count && job.taiwan_team_count > 0 && (
              <span className="bg-aurora-teal/20 text-aurora-teal px-4 py-2 rounded-full border border-aurora-teal/30">
                {job.taiwan_team_count} Asia team {job.taiwan_team_count === 1 ? 'member' : 'members'}
              </span>
            )}
            {job.industry && (
              <span className="bg-aurora-purple/20 text-aurora-purple px-4 py-2 rounded-full border border-aurora-purple/30">
                {job.industry}
              </span>
            )}
            {job.company_size && (
              <span className="bg-midnight/50 text-frost/70 px-4 py-2 rounded-full border border-midnight">
                {job.company_size} employees
              </span>
            )}
            {job.job_type && (
              <span className="bg-midnight/50 text-frost/70 px-4 py-2 rounded-full border border-midnight">
                {job.job_type}
              </span>
            )}
          </div>

          {/* Apply button */}
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-8 py-3 bg-gradient-to-r from-aurora-teal to-aurora-green text-void font-bold rounded-lg hover:shadow-lg hover:shadow-aurora-teal/50 transition-all duration-300 hover:scale-105"
          >
            Apply on {job.board_source}
          </a>
        </div>

        {/* Job description */}
        <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 mb-6 slide-up stagger-1">
          <h2 className="text-2xl font-bold text-frost mb-4">Job Description</h2>
          <div
            className="prose prose-invert max-w-none text-frost/80"
            dangerouslySetInnerHTML={{ __html: job.description }}
          />
        </div>

        {/* Company info */}
        {company && (
          <div className="card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-8 slide-up stagger-2">
            <h2 className="text-2xl font-bold text-frost mb-4">About {company.name}</h2>
            {company.description && (
              <p className="text-frost/80 mb-4">{company.description}</p>
            )}
            <div className="grid grid-cols-2 gap-4 mb-6">
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
              {company.total_employees && (
                <div>
                  <div className="text-frost/50 text-sm mb-1">Company Size</div>
                  <div className="text-frost font-semibold">{company.total_employees} employees</div>
                </div>
              )}
              {company.taiwan_employee_count && (
                <div>
                  <div className="text-frost/50 text-sm mb-1">Asia Team</div>
                  <div className="text-aurora-teal font-semibold">{company.taiwan_employee_count} members</div>
                </div>
              )}
            </div>
            <div className="flex gap-4">
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
                  LinkedIn →
                </a>
              )}
              {company.website && (
                <a
                  href={company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-6 py-2 bg-midnight/50 text-frost border border-midnight rounded-lg hover:bg-midnight transition-all"
                >
                  Website →
                </a>
              )}
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="mt-6 text-center text-frost/40 text-sm slide-up stagger-3">
          Posted {formatDate(job.posted_date)} • Source: {job.board_source}
        </div>
      </div>
    </div>
  );
}

import Link from 'next/link';
import { Job } from '@/lib/db';

interface JobCardProps {
  job: Job;
  index?: number;
}

export default function JobCard({ job, index = 0 }: JobCardProps) {
  const staggerClass = index < 5 ? `stagger-${index + 1}` : '';

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  return (
    <div className={`card-glow bg-deep/50 backdrop-blur-sm border border-midnight/50 rounded-lg p-6 slide-up ${staggerClass} group hover:scale-[1.02] transition-transform duration-300`}>
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-xl font-bold text-aurora-teal mb-2 group-hover:glow-teal transition-all">
            <Link href={`/jobs/${job.id}`} className="hover:underline">
              {job.title}
            </Link>
          </h3>
          <div className="flex items-center gap-3 text-sm text-frost/70">
            {job.company_id ? (
              <Link
                href={`/companies/${job.company_id}`}
                className="text-aurora-purple hover:glow-purple font-semibold transition-all"
              >
                {job.company}
              </Link>
            ) : (
              <span className="text-aurora-purple font-semibold">{job.company}</span>
            )}
            <span>•</span>
            <span>{job.location}</span>
            {job.remote_type && (
              <>
                <span>•</span>
                <span className="text-aurora-green">{job.remote_type}</span>
              </>
            )}
          </div>
        </div>
        {job.ranking_score && job.ranking_score > 0 && (
          <div className="ml-4 flex flex-col items-end">
            <div className="text-shimmer font-bold text-2xl glow-pink">
              {job.ranking_score.toFixed(1)}
            </div>
            <div className="text-xs text-frost/50 uppercase tracking-wider">Score</div>
          </div>
        )}
      </div>

      {job.description && (
        <p className="text-frost/80 text-sm mb-4 line-clamp-3">
          {job.description.replace(/<[^>]*>/g, '').substring(0, 200)}...
        </p>
      )}

      <div className="flex flex-wrap gap-2 items-center text-xs">
        {job.taiwan_team_count && job.taiwan_team_count > 0 && (
          <span className="bg-aurora-teal/20 text-aurora-teal px-3 py-1 rounded-full border border-aurora-teal/30">
            {job.taiwan_team_count} Asia team {job.taiwan_team_count === 1 ? 'member' : 'members'}
          </span>
        )}
        {job.industry && (
          <span className="bg-aurora-purple/20 text-aurora-purple px-3 py-1 rounded-full border border-aurora-purple/30">
            {job.industry}
          </span>
        )}
        {job.company_size && (
          <span className="bg-midnight/50 text-frost/70 px-3 py-1 rounded-full border border-midnight">
            {job.company_size} employees
          </span>
        )}
        {job.job_type && (
          <span className="bg-midnight/50 text-frost/70 px-3 py-1 rounded-full border border-midnight">
            {job.job_type}
          </span>
        )}
        <span className="ml-auto text-frost/50">
          {formatDate(job.posted_date)}
        </span>
      </div>
    </div>
  );
}

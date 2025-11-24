import { getJobs, searchJobs } from '@/lib/db';
import JobCard from '@/components/JobCard';
import SearchBar from '@/components/SearchBar';

export const dynamic = 'force-dynamic';

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const query = typeof params.q === 'string' ? params.q : undefined;
  const jobs = query ? searchJobs(query, 100) : getJobs(100, 0);

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="text-center mb-12 fade-in">
        <h2 className="text-5xl font-bold mb-4 bg-gradient-to-r from-aurora-teal via-aurora-purple to-aurora-pink bg-clip-text text-transparent">
          Discover Your Next Adventure
        </h2>
        <p className="text-frost/60 text-lg">
          {jobs.length} opportunities ranked by relevance and Asia team presence
        </p>
      </div>

      <SearchBar />

      {query && (
        <div className="mb-6 text-center slide-up">
          <p className="text-frost/70">
            Found <span className="text-aurora-teal font-bold">{jobs.length}</span> results for{' '}
            <span className="text-aurora-purple font-bold">&ldquo;{query}&rdquo;</span>
          </p>
        </div>
      )}

      <div className="grid gap-6">
        {jobs.length > 0 ? (
          jobs.map((job, index) => (
            <JobCard key={job.id} job={job} index={index} />
          ))
        ) : (
          <div className="text-center py-20 slide-up">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-2xl font-bold text-frost/70 mb-2">No jobs found</h3>
            <p className="text-frost/50">Try adjusting your search terms</p>
          </div>
        )}
      </div>
    </div>
  );
}

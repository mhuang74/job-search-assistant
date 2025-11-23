import { NextRequest, NextResponse } from 'next/server';
import { getJobs, searchJobs } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q');
    const limit = parseInt(searchParams.get('limit') || '100');
    const minTaiwanTeam = parseInt(searchParams.get('minTaiwanTeam') || '0');

    let jobs;
    if (query) {
      jobs = searchJobs(query, limit);
    } else {
      jobs = getJobs(limit, minTaiwanTeam);
    }

    return NextResponse.json({ jobs, count: jobs.length });
  } catch (error) {
    console.error('Error fetching jobs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch jobs' },
      { status: 500 }
    );
  }
}

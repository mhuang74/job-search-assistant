import { NextRequest, NextResponse } from 'next/server';
import { getCompanyById, getJobsByCompany, getTeamMembersByCompany, getCountriesByCompany } from '@/lib/db';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const company = getCompanyById(id);

    if (!company) {
      return NextResponse.json(
        { error: 'Company not found' },
        { status: 404 }
      );
    }

    const jobs = getJobsByCompany(id);
    const teamMembers = getTeamMembersByCompany(id);
    const countries = getCountriesByCompany(id);

    return NextResponse.json({
      ...company,
      jobs,
      teamMembers,
      countries,
    });
  } catch (error) {
    console.error('Error fetching company:', error);
    return NextResponse.json(
      { error: 'Failed to fetch company' },
      { status: 500 }
    );
  }
}

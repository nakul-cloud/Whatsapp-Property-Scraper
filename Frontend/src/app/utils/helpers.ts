import { PropertyLead, KPIData, ChartDataPoint } from '../types';

function extractNumericPrice(value: unknown): number {
  if (value === null || value === undefined) {
    return 0;
  }

  const normalized = String(value).replace(/[^\d.]/g, '');
  return normalized ? parseFloat(normalized) : 0;
}

export function calculateKPIs(leads: PropertyLead[]): KPIData {
  if (leads.length === 0) {
    return {
      totalLeads: 0,
      uniqueContacts: 0,
      avgPrice: 0,
      dataQuality: 0,
    };
  }

  const uniqueContacts = new Set(
    leads.map((l) => l.owner_contact).filter((c) => c && c !== 'N/A')
  ).size;

  const prices = leads
    .map((l) => extractNumericPrice(l.rent_or_sell_price))
    .filter((p) => p > 0);

  const avgPrice = prices.length > 0
    ? prices.reduce((a, b) => a + b, 0) / prices.length
    : 0;

  const filledFields = leads.reduce((acc, lead) => {
    const fields = Object.values(lead).filter(
      (v) => v && v !== 'N/A' && v.toString().trim() !== ''
    );
    return acc + fields.length;
  }, 0);

  const totalFields = leads.length * Object.keys(leads[0] || {}).length;
  const dataQuality = totalFields > 0 ? (filledFields / totalFields) * 100 : 0;

  return {
    totalLeads: leads.length,
    uniqueContacts,
    avgPrice,
    dataQuality: Math.round(dataQuality),
  };
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

export function getPropertyTypeDistribution(
  leads: PropertyLead[]
): ChartDataPoint[] {
  const distribution = leads.reduce((acc, lead) => {
    const type = lead.property_type || 'Unknown';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return Object.entries(distribution)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

export function getTopAreas(leads: PropertyLead[], limit = 12): ChartDataPoint[] {
  const areaCounts = leads.reduce((acc, lead) => {
    const area = lead.area || 'Unknown';
    if (area !== 'N/A' && area.trim()) {
      acc[area] = (acc[area] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  return Object.entries(areaCounts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

export function getPriceDistribution(leads: PropertyLead[]): ChartDataPoint[] {
  const prices = leads
    .map((l) => extractNumericPrice(l.rent_or_sell_price))
    .filter((p) => p > 0);

  if (prices.length === 0) return [];

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const binCount = 10;
  const binSize = (max - min) / binCount;

  const bins: ChartDataPoint[] = [];
  for (let i = 0; i < binCount; i++) {
    const rangeStart = min + i * binSize;
    const rangeEnd = min + (i + 1) * binSize;
    const count = prices.filter((p) => p >= rangeStart && p < rangeEnd).length;

    bins.push({
      name: `${formatCurrency(rangeStart)}-${formatCurrency(rangeEnd)}`,
      value: count,
    });
  }

  return bins;
}

export function getTimelineData(leads: PropertyLead[]): ChartDataPoint[] {
  const timeline = leads.reduce((acc, lead) => {
    const date = lead.date_stamp || 'Unknown';
    if (!acc[date]) {
      acc[date] = { date, leads: 0, missingContact: 0 };
    }
    acc[date].leads += 1;
    if (!lead.owner_contact || lead.owner_contact === 'N/A') {
      acc[date].missingContact += 1;
    }
    return acc;
  }, {} as Record<string, any>);

  return Object.values(timeline).sort((a: any, b: any) =>
    a.date.localeCompare(b.date)
  );
}

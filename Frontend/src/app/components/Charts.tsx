import { motion } from 'motion/react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { ChartDataPoint } from '../types';

interface ChartContainerProps {
  title: string;
  children: React.ReactNode;
  delay?: number;
}

function ChartContainer({ title, children, delay = 0 }: ChartContainerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-card rounded-xl p-6 border border-border"
    >
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="w-full h-[300px]">{children}</div>
    </motion.div>
  );
}

interface TimelineChartProps {
  data: ChartDataPoint[];
  delay?: number;
}

export function TimelineChart({ data, delay }: TimelineChartProps) {
  return (
    <ChartContainer title="Data Extraction Timeline" delay={delay}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
          <XAxis
            dataKey="date"
            stroke="#888"
            tick={{ fontSize: 12 }}
            tickLine={false}
          />
          <YAxis stroke="#888" tick={{ fontSize: 12 }} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--popover)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="leads"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ fill: '#6366f1' }}
            name="Leads"
          />
          <Line
            type="monotone"
            dataKey="missingContact"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ fill: '#ef4444' }}
            name="Missing Contact"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

interface PropertyTypeChartProps {
  data: ChartDataPoint[];
  delay?: number;
}

export function PropertyTypeChart({ data, delay }: PropertyTypeChartProps) {
  return (
    <ChartContainer title="Property Type Distribution" delay={delay}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="horizontal">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
          <XAxis type="number" stroke="#888" tick={{ fontSize: 12 }} tickLine={false} />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#888"
            tick={{ fontSize: 12 }}
            tickLine={false}
            width={80}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--popover)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
            }}
          />
          <Bar dataKey="value" fill="#10b981" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

interface TopAreasChartProps {
  data: ChartDataPoint[];
  delay?: number;
}

export function TopAreasChart({ data, delay }: TopAreasChartProps) {
  return (
    <ChartContainer title="Top Areas by Frequency" delay={delay}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
          <XAxis
            dataKey="name"
            stroke="#888"
            tick={{ fontSize: 11, angle: -45, textAnchor: 'end' }}
            height={80}
            tickLine={false}
          />
          <YAxis stroke="#888" tick={{ fontSize: 12 }} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--popover)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
            }}
          />
          <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

interface PriceDistributionChartProps {
  data: ChartDataPoint[];
  delay?: number;
}

export function PriceDistributionChart({
  data,
  delay,
}: PriceDistributionChartProps) {
  return (
    <ChartContainer title="Price Distribution" delay={delay}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
          <XAxis
            dataKey="name"
            stroke="#888"
            tick={{ fontSize: 10, angle: -45, textAnchor: 'end' }}
            height={100}
            tickLine={false}
          />
          <YAxis stroke="#888" tick={{ fontSize: 12 }} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--popover)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
            }}
          />
          <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

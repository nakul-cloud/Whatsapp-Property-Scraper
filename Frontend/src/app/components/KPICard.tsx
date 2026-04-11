import { motion } from 'motion/react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  accentColor?: string;
  delay?: number;
}

export function KPICard({
  title,
  value,
  trend,
  accentColor = '#6366f1',
  delay = 0,
}: KPICardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="relative bg-card rounded-xl p-6 border border-border overflow-hidden group hover:shadow-lg transition-shadow"
    >
      <div
        className="absolute left-0 top-0 bottom-0 w-1"
        style={{ background: accentColor }}
      />

      <div className="relative z-10">
        <p className="text-sm text-muted-foreground mb-2">{title}</p>
        <div className="flex items-end justify-between">
          <motion.p
            initial={{ scale: 0.5 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: delay + 0.2 }}
            className="text-3xl font-semibold text-foreground"
          >
            {value}
          </motion.p>
          {trend && (
            <div
              className={`flex items-center gap-1 text-sm ${
                trend.isPositive ? 'text-green-500' : 'text-red-500'
              }`}
            >
              {trend.isPositive ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span>{Math.abs(trend.value)}%</span>
            </div>
          )}
        </div>
      </div>

      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity"
        style={{ background: accentColor }}
      />
    </motion.div>
  );
}

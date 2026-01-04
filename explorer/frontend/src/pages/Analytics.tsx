import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { ArrowRightLeft, Blocks, Users, Cpu, TrendingUp, Clock, Activity } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { Loading } from '../components/Loading';
import {
  getTransactionAnalytics,
  getBlockAnalytics,
  getAddressAnalytics,
  getAIAnalytics,
} from '../api/client';
import { formatNumber, formatXAI } from '../utils/format';

type Period = '1h' | '24h' | '7d' | '30d';

const PERIODS: { value: Period; label: string }[] = [
  { value: '1h', label: '1 Hour' },
  { value: '24h', label: '24 Hours' },
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
];

const CHART_COLORS = {
  primary: '#6366f1',
  secondary: '#22c55e',
  tertiary: '#f59e0b',
  quaternary: '#ef4444',
  muted: '#64748b',
};

const PIE_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

function formatTimestamp(timestamp: string, period: Period): string {
  const date = new Date(timestamp);
  if (period === '1h') return format(date, 'HH:mm');
  if (period === '24h') return format(date, 'HH:00');
  if (period === '7d') return format(date, 'EEE');
  return format(date, 'MMM d');
}

export function Analytics() {
  const [period, setPeriod] = useState<Period>('24h');

  const { data: txAnalytics, isLoading: txLoading } = useQuery({
    queryKey: ['transactionAnalytics', period],
    queryFn: () => getTransactionAnalytics(period),
  });

  const { data: blockAnalytics, isLoading: blockLoading } = useQuery({
    queryKey: ['blockAnalytics', period],
    queryFn: () => getBlockAnalytics(period),
  });

  const { data: addressAnalytics, isLoading: addressLoading } = useQuery({
    queryKey: ['addressAnalytics', period],
    queryFn: () => getAddressAnalytics(period),
  });

  const { data: aiAnalytics, isLoading: aiLoading } = useQuery({
    queryKey: ['aiAnalytics', period],
    queryFn: () => getAIAnalytics(period),
  });

  const isLoading = txLoading || blockLoading || addressLoading || aiLoading;

  // Transform data for charts
  const txChartData = txAnalytics?.timeline.map(d => ({
    ...d,
    time: formatTimestamp(d.timestamp, period),
  })) || [];

  const blockChartData = blockAnalytics?.timeline.map(d => ({
    ...d,
    time: formatTimestamp(d.timestamp, period),
  })) || [];

  const addressChartData = addressAnalytics?.timeline.map(d => ({
    ...d,
    time: formatTimestamp(d.timestamp, period),
  })) || [];

  const aiChartData = aiAnalytics?.timeline.map(d => ({
    ...d,
    time: formatTimestamp(d.timestamp, period),
  })) || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Network Analytics</h1>
          <p className="text-xai-muted mt-1">Real-time blockchain metrics and trends</p>
        </div>

        {/* Period Selector */}
        <div className="flex gap-2 bg-xai-card rounded-lg p-1">
          {PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                period === p.value
                  ? 'bg-xai-primary text-white'
                  : 'text-xai-muted hover:text-white'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Transactions"
          value={isLoading ? '...' : formatNumber(txAnalytics?.summary.total_transactions || 0)}
          icon={ArrowRightLeft}
        />
        <StatCard
          label="Total Blocks"
          value={isLoading ? '...' : formatNumber(blockAnalytics?.summary.total_blocks || 0)}
          icon={Blocks}
        />
        <StatCard
          label="Active Addresses"
          value={isLoading ? '...' : formatNumber(addressAnalytics?.summary.peak_active || 0)}
          icon={Users}
        />
        <StatCard
          label="AI Tasks"
          value={isLoading ? '...' : formatNumber(aiAnalytics?.summary.total_tasks || 0)}
          icon={Cpu}
        />
      </div>

      {isLoading ? (
        <Loading />
      ) : (
        <>
          {/* Transaction Volume Chart */}
          <Card>
            <CardHeader
              title="Transaction Volume"
              action={
                <div className="flex items-center gap-2 text-sm text-xai-muted">
                  <span>Peak: {txAnalytics?.summary.peak_transactions}</span>
                  <span className="text-xai-border">|</span>
                  <span>Avg: {txAnalytics?.summary.avg_transactions_per_interval.toFixed(0)}</span>
                </div>
              }
            />
            <div className="h-80 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={txChartData}>
                  <defs>
                    <linearGradient id="colorTx" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#fff' }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="transaction_count"
                    name="Transactions"
                    stroke={CHART_COLORS.primary}
                    fillOpacity={1}
                    fill="url(#colorTx)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Transaction Types Breakdown */}
          <div className="grid lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader title="Transaction Types" />
              <div className="h-72 mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={txChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                      }}
                    />
                    <Legend />
                    <Bar dataKey="transfer_transactions" name="Transfers" fill={CHART_COLORS.primary} stackId="stack" />
                    <Bar dataKey="ai_transactions" name="AI Tasks" fill={CHART_COLORS.secondary} stackId="stack" />
                    <Bar dataKey="contract_transactions" name="Contracts" fill={CHART_COLORS.tertiary} stackId="stack" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardHeader title="Transaction Volume (XAI)" />
              <div className="h-72 mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={txChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                      }}
                      formatter={(value) => [formatXAI(value as number), 'Volume']}
                    />
                    <Line
                      type="monotone"
                      dataKey="volume"
                      name="Volume"
                      stroke={CHART_COLORS.secondary}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          {/* Block Production Chart */}
          <Card>
            <CardHeader
              title="Block Production"
              action={
                <div className="flex items-center gap-2 text-sm text-xai-muted">
                  <Clock className="h-4 w-4" />
                  <span>Avg Block Time: {blockAnalytics?.summary.avg_block_time.toFixed(1)}s</span>
                </div>
              }
            />
            <div className="h-80 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={blockChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
                  <YAxis yAxisId="left" stroke="#9ca3af" fontSize={12} />
                  <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="blocks_produced"
                    name="Blocks"
                    stroke={CHART_COLORS.primary}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="avg_block_time"
                    name="Block Time (s)"
                    stroke={CHART_COLORS.tertiary}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Active Addresses Chart */}
          <Card>
            <CardHeader
              title="Active Addresses"
              action={
                <div className="flex items-center gap-2 text-sm text-xai-muted">
                  <TrendingUp className="h-4 w-4" />
                  <span>New Addresses: {formatNumber(addressAnalytics?.summary.total_new || 0)}</span>
                </div>
              }
            />
            <div className="h-80 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={addressChartData}>
                  <defs>
                    <linearGradient id="colorActive" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.secondary} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={CHART_COLORS.secondary} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorNew" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.tertiary} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={CHART_COLORS.tertiary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="active_addresses"
                    name="Active"
                    stroke={CHART_COLORS.secondary}
                    fillOpacity={1}
                    fill="url(#colorActive)"
                  />
                  <Area
                    type="monotone"
                    dataKey="new_addresses"
                    name="New"
                    stroke={CHART_COLORS.tertiary}
                    fillOpacity={1}
                    fill="url(#colorNew)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* AI Analytics Section */}
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Activity className="h-6 w-6 text-xai-primary" />
              AI Compute Analytics
            </h2>

            {/* AI Summary Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label="Total AI Tasks"
                value={formatNumber(aiAnalytics?.summary.total_tasks || 0)}
                icon={Cpu}
              />
              <StatCard
                label="Completed Tasks"
                value={formatNumber(aiAnalytics?.summary.completed_tasks || 0)}
                icon={TrendingUp}
              />
              <StatCard
                label="Total Compute Cost"
                value={formatXAI(aiAnalytics?.summary.total_compute_cost || 0)}
                icon={ArrowRightLeft}
              />
              <StatCard
                label="Avg Active Providers"
                value={formatNumber(aiAnalytics?.summary.average_providers || 0)}
                icon={Users}
              />
            </div>

            {/* AI Tasks Timeline */}
            <Card>
              <CardHeader title="AI Task Activity" />
              <div className="h-72 mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={aiChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="tasks_created"
                      name="Created"
                      stroke={CHART_COLORS.primary}
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="tasks_completed"
                      name="Completed"
                      stroke={CHART_COLORS.secondary}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* AI Distribution Charts */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader title="Task Types Distribution" />
                <div className="h-72 mt-4 flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={aiAnalytics?.task_types || []}
                        dataKey="count"
                        nameKey="type"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ name, percent }: { name?: string; percent?: number }) => `${name || ''}: ${((percent || 0) * 100).toFixed(1)}%`}
                        labelLine={{ stroke: '#9ca3af' }}
                      >
                        {(aiAnalytics?.task_types || []).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card>
                <CardHeader title="AI Model Usage" />
                <div className="h-72 mt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={aiAnalytics?.model_usage || []}
                      layout="vertical"
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis type="number" stroke="#9ca3af" fontSize={12} />
                      <YAxis dataKey="model" type="category" stroke="#9ca3af" fontSize={12} width={100} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                        formatter={(value) => [`${value} tasks`, 'Tasks']}
                      />
                      <Bar dataKey="tasks" fill={CHART_COLORS.primary}>
                        {(aiAnalytics?.model_usage || []).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

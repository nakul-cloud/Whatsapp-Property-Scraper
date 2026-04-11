import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Toaster, toast } from 'sonner';
import {
  MessageSquare,
  BarChart3,
  AlertCircle,
  FileJson,
  Download,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { PropertyLead, ProcessResponse, GroqConfig } from './types';
import {
  calculateKPIs,
  formatCurrency,
  getPropertyTypeDistribution,
  getTopAreas,
  getPriceDistribution,
  getTimelineData,
} from './utils/helpers';
import { processMessages, exportCSV } from './utils/api';
import { KPICard } from './components/KPICard';
import {
  TimelineChart,
  PropertyTypeChart,
  TopAreasChart,
  PriceDistributionChart,
} from './components/Charts';
import { LeadsTable } from './components/LeadsTable';
import { SettingsPanel } from './components/SettingsPanel';
import { MessageInput } from './components/MessageInput';
import { DemoDataButton, SAMPLE_MESSAGES } from './components/DemoDataButton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Button } from './components/ui/button';

export default function App() {
  const [activeTab, setActiveTab] = useState('input');
  const [leads, setLeads] = useState<PropertyLead[]>([]);
  const [combinedLeads, setCombinedLeads] = useState<PropertyLead[]>([]);
  const [metadata, setMetadata] = useState<ProcessResponse['meta'] | null>(
    null
  );
  const [isProcessing, setIsProcessing] = useState(false);
  const [groqConfig, setGroqConfig] = useState<GroqConfig>({
    enabled: false,
    apiKey: '',
    model: 'llama-3.1-70b-versatile',
  });
  const [customAreasPath, setCustomAreasPath] = useState('');

  useEffect(() => {
    const cached = window.localStorage.getItem('combinedLeads');
    if (cached) {
      try {
        setCombinedLeads(JSON.parse(cached));
      } catch {
        setCombinedLeads([]);
      }
    }
  }, []);

  const handleProcessMessages = async (messages: string) => {
    setIsProcessing(true);
    try {
      const response = await processMessages(
        messages,
        groqConfig.enabled ? groqConfig : undefined,
        customAreasPath
      );

      setLeads(response.rows ?? []);
      setMetadata((response.meta ?? response.metadata ?? null) as ProcessResponse['meta'] | null);
      setActiveTab('leads');

      toast.success(
        `Successfully processed ${(response.rows ?? []).length} leads from ${(response.meta ?? response.metadata)?.message_count ?? 0} messages`
      );
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to process messages'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const blob = await exportCSV(leads);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leads_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('CSV exported successfully');
    } catch (error) {
      toast.error('Failed to export CSV');
    }
  };

  const handleExportCombinedCSV = async () => {
    const rows = combinedLeads.length > 0 ? combinedLeads : leads;

    if (rows.length === 0) {
      toast.error('No combined data available');
      return;
    }

    try {
      const blob = await exportCSV(rows);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `combined_leads_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Combined CSV exported successfully');
    } catch {
      toast.error('Failed to export combined CSV');
    }
  };

  const handleAddToCombined = () => {
    if (leads.length === 0) {
      toast.error('No leads available to add');
      return;
    }

    const nextCombined = [...combinedLeads, ...leads];
    setCombinedLeads(nextCombined);
    window.localStorage.setItem('combinedLeads', JSON.stringify(nextCombined));
    toast.success(`Added ${leads.length} leads to combined cache`);
  };

  const kpis = calculateKPIs(leads);
  const failedMessages =
    (metadata as any)?.audit_failed ??
    (metadata as any)?.failed_messages ??
    [];

  return (
    <div className="min-h-screen bg-background">
      <Toaster position="top-right" />

      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-primary via-primary/95 to-primary/90">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />
        <motion.div
          animate={{
            backgroundPosition: ['0% 0%', '100% 100%'],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
          className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-purple-600/20 to-pink-600/20 bg-[length:200%_200%]"
        />

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="relative"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
            <div className="text-center space-y-6">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full border border-white/20"
              >
                <Sparkles className="w-4 h-4 text-yellow-300" />
                <span className="text-sm text-white/90">AI-Powered Lead Extraction</span>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight"
              >
                WhatsApp Property
                <br />
                <span className="bg-gradient-to-r from-blue-300 via-purple-300 to-pink-300 bg-clip-text text-transparent">
                  Lead Extractor
                </span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="text-lg sm:text-xl text-white/80 max-w-2xl mx-auto"
              >
                Transform WhatsApp conversations into structured property leads with
                intelligent parsing and AI-powered extraction
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.5 }}
                className="flex flex-wrap items-center justify-center gap-4 pt-4"
              >
                <div className="flex items-center gap-2 text-white/70">
                  <TrendingUp className="w-5 h-5" />
                  <span className="text-sm">Real-time Processing</span>
                </div>
                <div className="flex items-center gap-2 text-white/70">
                  <BarChart3 className="w-5 h-5" />
                  <span className="text-sm">Advanced Analytics</span>
                </div>
                <div className="flex items-center gap-2 text-white/70">
                  <Sparkles className="w-5 h-5" />
                  <span className="text-sm">AI Fallback Support</span>
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="space-y-8">
          {/* Settings */}
          <SettingsPanel
            config={groqConfig}
            onConfigChange={setGroqConfig}
            customAreasPath={customAreasPath}
            onCustomAreasPathChange={setCustomAreasPath}
          />

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
              <TabsTrigger value="input" className="gap-2">
                <MessageSquare className="w-4 h-4" />
                <span className="hidden sm:inline">Input</span>
              </TabsTrigger>
              <TabsTrigger value="leads" className="gap-2">
                <FileJson className="w-4 h-4" />
                <span className="hidden sm:inline">Leads</span>
                {leads.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 bg-primary text-primary-foreground text-xs rounded-full">
                    {leads.length}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="analytics" className="gap-2">
                <BarChart3 className="w-4 h-4" />
                <span className="hidden sm:inline">Analytics</span>
              </TabsTrigger>
              <TabsTrigger value="failed" className="gap-2">
                <AlertCircle className="w-4 h-4" />
                <span className="hidden sm:inline">Failed</span>
                {failedMessages.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 bg-destructive text-destructive-foreground text-xs rounded-full">
                    {failedMessages.length}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>

            {/* Input Tab */}
            <TabsContent value="input" className="space-y-6 mt-6">
              <div className="flex justify-end">
                <DemoDataButton
                  onClick={() => handleProcessMessages(SAMPLE_MESSAGES)}
                  disabled={isProcessing}
                />
              </div>

              <MessageInput
                onProcess={handleProcessMessages}
                isProcessing={isProcessing}
              />

              {leads.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/20 rounded-xl p-6"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="space-y-1">
                      <h4 className="font-semibold text-lg mb-1">
                        Processing Complete
                      </h4>
                      <p className="text-sm text-muted-foreground">
                        {leads.length} leads extracted and ready for analysis
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" onClick={handleExportCSV}>
                        Separate CSV Download
                      </Button>
                      <Button variant="outline" onClick={handleAddToCombined}>
                        Add to Combined
                      </Button>
                      <Button onClick={handleExportCombinedCSV}>
                        Combined CSV Download
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )}
            </TabsContent>

            {/* Leads Tab */}
            <TabsContent value="leads" className="space-y-6 mt-6">
              {leads.length === 0 ? (
                <div className="bg-card border border-border rounded-xl p-12 text-center">
                  <FileJson className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Leads Yet</h3>
                  <p className="text-muted-foreground mb-6">
                    Process WhatsApp messages to see extracted leads here
                  </p>
                  <Button onClick={() => setActiveTab('input')}>
                    Go to Input
                  </Button>
                </div>
              ) : (
                <>
                  <div className="flex flex-wrap gap-2 justify-end">
                    <Button variant="outline" onClick={handleExportCSV}>
                      Separate CSV Download
                    </Button>
                    <Button variant="outline" onClick={handleAddToCombined}>
                      Add to Combined
                    </Button>
                    <Button onClick={handleExportCombinedCSV}>
                      Combined CSV Download
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <KPICard
                      title="Total Leads"
                      value={kpis.totalLeads}
                      accentColor="#6366f1"
                      delay={0}
                    />
                    <KPICard
                      title="Unique Contacts"
                      value={kpis.uniqueContacts}
                      accentColor="#10b981"
                      delay={0.1}
                    />
                    <KPICard
                      title="Avg Price/Rent"
                      value={formatCurrency(kpis.avgPrice)}
                      accentColor="#f59e0b"
                      delay={0.2}
                    />
                    <KPICard
                      title="Data Quality"
                      value={`${kpis.dataQuality}%`}
                      accentColor="#8b5cf6"
                      delay={0.3}
                    />
                  </div>

                  <LeadsTable leads={leads} onExport={handleExportCSV} />
                </>
              )}
            </TabsContent>

            {/* Analytics Tab */}
            <TabsContent value="analytics" className="space-y-6 mt-6">
              {leads.length === 0 ? (
                <div className="bg-card border border-border rounded-xl p-12 text-center">
                  <BarChart3 className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">
                    No Analytics Available
                  </h3>
                  <p className="text-muted-foreground mb-6">
                    Process WhatsApp messages to see analytics and charts
                  </p>
                  <Button onClick={() => setActiveTab('input')}>
                    Go to Input
                  </Button>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <KPICard
                      title="Total Leads"
                      value={kpis.totalLeads}
                      accentColor="#6366f1"
                      delay={0}
                    />
                    <KPICard
                      title="Unique Contacts"
                      value={kpis.uniqueContacts}
                      accentColor="#10b981"
                      delay={0.1}
                    />
                    <KPICard
                      title="Avg Price/Rent"
                      value={formatCurrency(kpis.avgPrice)}
                      accentColor="#f59e0b"
                      delay={0.2}
                    />
                    <KPICard
                      title="Data Quality"
                      value={`${kpis.dataQuality}%`}
                      accentColor="#8b5cf6"
                      delay={0.3}
                    />
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <TimelineChart data={getTimelineData(leads)} delay={0} />
                    <PropertyTypeChart
                      data={getPropertyTypeDistribution(leads)}
                      delay={0.1}
                    />
                    <TopAreasChart data={getTopAreas(leads)} delay={0.2} />
                    <PriceDistributionChart
                      data={getPriceDistribution(leads)}
                      delay={0.3}
                    />
                  </div>
                </>
              )}
            </TabsContent>

            {/* Failed Messages Tab */}
            <TabsContent value="failed" className="space-y-6 mt-6">
              {failedMessages.length === 0 ? (
                <div className="bg-card border border-border rounded-xl p-12 text-center">
                  <AlertCircle className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">
                    No Failed Messages
                  </h3>
                  <p className="text-muted-foreground">
                    All messages were processed successfully
                  </p>
                </div>
              ) : (
                <div className="bg-card border border-border rounded-xl overflow-hidden">
                  <div className="p-4 border-b border-border flex justify-between items-center">
                    <h3 className="font-semibold">Failed Messages Audit</h3>
                    <Button variant="outline" size="sm">
                      <Download className="w-4 h-4 mr-2" />
                      Export Failed
                    </Button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-3 text-left text-sm font-medium">
                            Index
                          </th>
                          <th className="px-4 py-3 text-left text-sm font-medium">
                            Date
                          </th>
                          <th className="px-4 py-3 text-left text-sm font-medium">
                            Missing Fields
                          </th>
                          <th className="px-4 py-3 text-left text-sm font-medium">
                            Raw Message
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {failedMessages.map((msg: any, idx: number) => (
                          <tr
                            key={idx}
                            className="border-b border-border hover:bg-muted/30"
                          >
                            <td className="px-4 py-3 text-sm">
                              {msg.idx ?? msg.message_index ?? idx + 1}
                            </td>
                            <td className="px-4 py-3 text-sm">
                              {msg.date_stamp}
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <div className="flex flex-wrap gap-1">
                                {Array.isArray(msg.missing_fields) ? (
                                  msg.missing_fields.map((field: string) => (
                                    <span
                                      key={field}
                                      className="px-2 py-0.5 bg-destructive/10 text-destructive text-xs rounded"
                                    >
                                      {field}
                                    </span>
                                  ))
                                ) : (
                                  <span className="px-2 py-0.5 bg-destructive/10 text-destructive text-xs rounded">
                                    {msg.missing_fields}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm max-w-md truncate font-mono text-muted-foreground">
                              {msg.raw_message}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-24 border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-muted-foreground">
            <p>
              WhatsApp Property Lead Extractor &copy; {new Date().getFullYear()}
            </p>
            <p className="mt-1">
              Powered by FastAPI + React + AI Technology
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
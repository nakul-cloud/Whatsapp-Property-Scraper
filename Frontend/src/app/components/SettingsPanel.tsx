import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Settings, ChevronDown, ChevronUp, Info } from 'lucide-react';
import { GroqConfig } from '../types';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import { Label } from './ui/label';

interface SettingsPanelProps {
  config: GroqConfig;
  onConfigChange: (config: GroqConfig) => void;
  customAreasPath: string;
  onCustomAreasPathChange: (path: string) => void;
}

export function SettingsPanel({
  config,
  onConfigChange,
  customAreasPath,
  onCustomAreasPathChange,
}: SettingsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showGroqConfig, setShowGroqConfig] = useState(false);

  const models = [
    'llama-3.1-70b-versatile',
    'llama-3.1-8b-instant',
    'mixtral-8x7b-32768',
    'Custom...',
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-card border border-border rounded-xl overflow-hidden"
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Settings</h3>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-5 h-5 text-muted-foreground" />
        )}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-border"
          >
            <div className="p-6 space-y-6">
              {/* AI Fallback Toggle */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="flex items-center gap-2">
                      AI Fallback (Groq)
                      <Info className="w-4 h-4 text-muted-foreground" />
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Use AI when regex parsing fails
                    </p>
                  </div>
                  <Switch
                    checked={config.enabled}
                    onCheckedChange={(enabled) => {
                      onConfigChange({ ...config, enabled });
                      setShowGroqConfig(enabled);
                    }}
                  />
                </div>

                {/* Groq Configuration */}
                <AnimatePresence>
                  {config.enabled && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="space-y-4 pl-4 border-l-2 border-primary/20"
                    >
                      <div className="space-y-2">
                        <Label htmlFor="groq-api-key">Groq API Key</Label>
                        <Input
                          id="groq-api-key"
                          type="password"
                          placeholder="gsk_..."
                          value={config.apiKey}
                          onChange={(e) =>
                            onConfigChange({
                              ...config,
                              apiKey: e.target.value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="groq-model">Model</Label>
                        <select
                          id="groq-model"
                          value={
                            models.includes(config.model)
                              ? config.model
                              : 'Custom...'
                          }
                          onChange={(e) => {
                            if (e.target.value !== 'Custom...') {
                              onConfigChange({
                                ...config,
                                model: e.target.value,
                              });
                            }
                          }}
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
                        >
                          {models.map((model) => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        </select>

                        {!models.includes(config.model) && (
                          <Input
                            placeholder="Enter custom model name"
                            value={config.model}
                            onChange={(e) =>
                              onConfigChange({
                                ...config,
                                model: e.target.value,
                              })
                            }
                          />
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Custom Areas File Path */}
              <div className="space-y-2">
                <Label htmlFor="custom-areas">Custom Pune Areas File (Optional)</Label>
                <Input
                  id="custom-areas"
                  type="text"
                  placeholder="/path/to/pune_areas.txt"
                  value={customAreasPath}
                  onChange={(e) => onCustomAreasPathChange(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Path to a custom file with additional Pune area names
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

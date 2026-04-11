import { useState } from 'react';
import { motion } from 'motion/react';
import { Send, Loader2, FileText } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

interface MessageInputProps {
  onProcess: (messages: string) => Promise<void>;
  isProcessing: boolean;
}

const SAMPLE_FORMAT = `Example format:
[12/04/2026, 10:30:45] John Doe: 2BHK for rent in Koregaon Park
Price: 25000/month, Deposit: 50000
Contact: 9876543210

[12/04/2026, 11:15:20] Jane Smith: 3BHK resale in Baner
1500 sqft, Price: 1.2 Cr
Call 9123456789`;

export function MessageInput({ onProcess, isProcessing }: MessageInputProps) {
  const [messages, setMessages] = useState('');
  const [charCount, setCharCount] = useState(0);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setMessages(text);
    setCharCount(text.length);
  };

  const handleSubmit = async () => {
    if (!messages.trim()) {
      toast.error('Please paste WhatsApp messages');
      return;
    }

    try {
      await onProcess(messages);
    } catch (error) {
      console.error('Processing error:', error);
    }
  };

  const estimatedMessages = messages.split(/\[\d{2}\/\d{2}\/\d{4}/).length - 1;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="bg-card border border-border rounded-xl overflow-hidden"
    >
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            <h3 className="font-semibold">WhatsApp Messages</h3>
          </div>
          {estimatedMessages > 0 && (
            <span className="text-sm text-muted-foreground">
              ~{estimatedMessages} messages detected
            </span>
          )}
        </div>

        <textarea
          value={messages}
          onChange={handleChange}
          placeholder={SAMPLE_FORMAT}
          disabled={isProcessing}
          className="w-full h-64 px-4 py-3 bg-background border border-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono text-sm disabled:opacity-50"
        />

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {charCount.toLocaleString()} characters
          </span>

          <Button
            onClick={handleSubmit}
            disabled={isProcessing || !messages.trim()}
            className="gap-2"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Process Messages
              </>
            )}
          </Button>
        </div>
      </div>
    </motion.div>
  );
}

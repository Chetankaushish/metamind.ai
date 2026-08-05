import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Sparkles, Bot, User, Send, Zap, RefreshCw, ChevronRight, MessageSquare,
  BarChart2, ShieldCheck, Cpu, ArrowUpRight, CheckCircle2, Sliders, Database, Eye
} from 'lucide-react';
import { sendCopilotPrompt, executeCopilotPlan, getCopilotContext } from '../../services/api';

interface CopilotViewProps {
  isMetaConnected: boolean;
  onOpenFacebookOAuthModal: () => void;
  onNavigateTab?: (tab: string) => void;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  suggestions?: string[];
  actionable?: {
    type: string;
    label: string;
    payload?: any;
  };
}

export const CopilotView: React.FC<CopilotViewProps> = ({
  isMetaConnected,
  onOpenFacebookOAuthModal,
  onNavigateTab
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      sender: 'assistant',
      text: "Hello! I am your Meta AI Copilot. I continually analyze your Meta ad campaigns, pixel events, and Advantage+ budgets to provide real-time optimization strategies. How can I assist you today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      suggestions: [
        'Analyze my top performing campaign',
        'Recommend budget scaling for high ROAS ad sets',
        'Check pixel & CAPI event matching quality',
        'Identify creative fatigue in active ads'
      ]
    }
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    async function loadContext() {
      try {
        await getCopilotContext();
      } catch (err) {
        console.error("Failed to load Copilot context:", err);
      }
    }
    loadContext();
  }, []);

  const handleSendMessage = async (textToSend?: string) => {
    const query = textToSend || inputPrompt;
    if (!query.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInputPrompt('');
    setIsTyping(true);

    try {
      const response = await sendCopilotPrompt(query);
      const replyText = response?.response || "No campaign data available for analysis.";
      
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: replyText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestions: [
          'Analyze my top performing campaign',
          'Export campaign telemetry report',
          'Refresh creative asset pool'
        ]
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const fallbackMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: "No campaign data available for analysis.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, fallbackMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="w-full max-w-[1700px] mx-auto space-y-6">
      {/* Copilot Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white shadow-xl border border-indigo-500/20">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-2xl bg-indigo-600/30 border border-indigo-500/40 text-indigo-400">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight flex items-center gap-2">
              Meta AI Copilot & Optimization Agent
            </h1>
            <p className="text-xs text-slate-300">
              Autonomous ad strategy assistant powered by Meta Marketing Graph API & Advantage+ ML
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold">
          <span className="px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            Autonomous Agent Active
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Interface Column */}
        <div className="lg:col-span-2 p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col h-[650px]">
          {/* Chat Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-3 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.sender === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div className={`max-w-[80%] space-y-2 ${m.sender === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed ${
                      m.sender === 'user'
                        ? 'bg-indigo-600 text-white font-medium shadow-md'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200/80 dark:border-slate-700/80'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{m.text}</p>
                    <span className={`text-[10px] block mt-1.5 ${m.sender === 'user' ? 'text-indigo-200' : 'text-slate-400'}`}>
                      {m.timestamp}
                    </span>
                  </div>

                  {m.suggestions && m.suggestions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {m.suggestions.map((sug, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(sug)}
                          className="px-2.5 py-1 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 hover:bg-indigo-100 text-indigo-600 dark:text-indigo-300 border border-indigo-200/60 dark:border-indigo-800/60 text-[11px] font-semibold transition cursor-pointer flex items-center gap-1"
                        >
                          <Zap className="w-3 h-3 text-amber-500" />
                          <span>{sug}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {m.sender === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-slate-700 text-white flex items-center justify-center shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="flex gap-3 justify-start items-center">
                <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-3.5 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-500" />
                  <span>Analyzing Meta Graph API signals...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                placeholder="Ask Meta AI Copilot (e.g. 'How can I scale my ROAS?')..."
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                className="flex-1 px-4 py-2.5 rounded-2xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={!inputPrompt.trim() || isTyping}
                className="px-4 py-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold text-xs shadow-md transition flex items-center gap-1.5 cursor-pointer"
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>

        {/* AI Recommendations & Intelligence Side Panel */}
        <div className="space-y-4">
          <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
            <h3 className="text-sm font-extrabold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              Automated Optimization Presets
            </h3>

            <div className="space-y-3">
              {[
                {
                  title: 'Advantage+ Budget Scaling',
                  desc: 'Scale high-performing ad sets (+20% daily budget) with ROAS > 4.2x.',
                  action: 'Apply Budget Scale'
                },
                {
                  title: 'Creative Fatigue Mitigation',
                  desc: 'Auto-pause ads with frequency > 2.8 and decaying CTR (< 1.5%).',
                  action: 'Rotate Creatives'
                },
                {
                  title: 'Conversion API Event Matching',
                  desc: 'Enforce CAPI deduplication rules for 98.4% event match quality.',
                  action: 'Verify CAPI'
                }
              ].map((opt, idx) => (
                <div key={idx} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 space-y-2">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">{opt.title}</h4>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">{opt.desc}</p>
                  <button
                    onClick={() => handleSendMessage(`Execute: ${opt.title}`)}
                    className="w-full py-1.5 rounded-xl bg-indigo-600/10 hover:bg-indigo-600 hover:text-white text-indigo-600 dark:text-indigo-400 text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1"
                  >
                    <span>{opt.action}</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CopilotView;

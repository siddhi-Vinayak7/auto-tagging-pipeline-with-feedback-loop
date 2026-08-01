import React, { useState, useEffect } from 'react';
import { Tag, RefreshCw, X, Plus, CheckCircle, AlertCircle, Sparkles, BarChart3, Edit3, Circle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TAG_TAXONOMY = [
  "AI/ML",
  "Frontend",
  "Backend",
  "Product",
  "Design",
  "Career",
  "Funding",
  "General",
];

export default function App() {
  const [activeTab, setActiveTab] = useState('composer');
  const [apiStatus, setApiStatus] = useState('online'); // 'online' | 'offline'

  // Initial health check
  useEffect(() => {
    fetch(`${API_BASE}/`)
      .then(res => res.ok ? setApiStatus('online') : setApiStatus('offline'))
      .catch(() => setApiStatus('offline'));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans flex flex-col">
      {/* Header / Navbar */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur sticky top-0 z-10 shadow-xs">
        <div className="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-600 rounded-xl text-white shadow-md shadow-indigo-600/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold text-indigo-600 tracking-tight">
                  Auto-Tagging Pipeline
                </h1>
                <span className="bg-indigo-50 text-indigo-600 border border-indigo-100 text-[11px] font-mono font-medium px-2 py-0.5 rounded-full">
                  v0.2.0
                </span>
              </div>
              <p className="text-xs text-slate-500 font-mono">LLM Classification & Feedback Loop</p>
            </div>
          </div>

          <div className="flex items-center space-x-6">
            {/* Live API Status Indicator */}
            <div className="flex items-center space-x-2 bg-slate-100/80 px-3 py-1.5 rounded-full border border-slate-200">
              <span className={`w-2 h-2 rounded-full ${apiStatus === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
              <span className="font-mono text-xs font-semibold text-slate-600">
                API {apiStatus === 'online' ? 'Online' : 'Offline'}
              </span>
            </div>

            {/* View Navigation */}
            <nav className="flex space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
              <button
                onClick={() => setActiveTab('composer')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 text-xs font-mono font-semibold rounded-lg transition-all cursor-pointer ${
                  activeTab === 'composer'
                    ? 'bg-white text-indigo-600 shadow-sm border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Composer</span>
              </button>

              <button
                onClick={() => setActiveTab('metrics')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 text-xs font-mono font-semibold rounded-lg transition-all cursor-pointer ${
                  activeTab === 'metrics'
                    ? 'bg-white text-indigo-600 shadow-sm border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Metrics</span>
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6">
        {activeTab === 'composer' ? (
          <ComposerView setApiStatus={setApiStatus} />
        ) : (
          <MetricsView setApiStatus={setApiStatus} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-4 text-center text-xs font-mono text-slate-400">
        Auto-Tagging Feedback System &bull; Fast-API & Groq (llama-3.3-70b)
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// View 1: Composer Component (Light Mode Restyled)
// ---------------------------------------------------------------------------
function ComposerView({ setApiStatus }) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  
  // Suggestion State
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState(null); // { post_id, suggestion_id, suggested_tags, was_fallback }
  const [currentChips, setCurrentChips] = useState([]);
  
  // Status & Error handling
  const [error, setError] = useState(null); // { message, isNetwork, isConflict, isValidationError }
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [selectedTagToAdd, setSelectedTagToAdd] = useState('');

  const handleSuggest = async (e) => {
    e?.preventDefault();
    if (!title.trim() || !body.trim()) {
      setError({ message: 'Both title and body are required and cannot be empty.', isValidationError: true });
      return;
    }

    setLoading(true);
    setError(null);
    setSuggestion(null);
    setConfirmed(false);

    try {
      const res = await fetch(`${API_BASE}/api/suggest-tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), body: body.trim() }),
      });

      const data = await res.json();
      setApiStatus('online');

      if (!res.ok) {
        if (res.status === 422) {
          const detail = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(', ') : data.detail;
          setError({ message: detail || 'Validation error', isValidationError: true });
        } else if (res.status === 502) {
          setError({ message: data.detail || 'LLM provider failed or timed out.', isNetwork: true });
        } else {
          setError({ message: data.detail || `Server error (${res.status})`, isNetwork: true });
        }
        setLoading(false);
        return;
      }

      setSuggestion(data);
      setCurrentChips(data.suggested_tags || []);
    } catch (err) {
      setApiStatus('offline');
      setError({ message: 'Failed to connect to server. Check backend connection.', isNetwork: true });
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveChip = (tagToRemove) => {
    if (confirmed) return;
    setCurrentChips(prev => prev.filter(t => t !== tagToRemove));
  };

  const handleAddTag = (tagToAdd) => {
    if (confirmed || !tagToAdd) return;
    if (currentChips.includes(tagToAdd)) return;
    if (currentChips.length >= 3) {
      setError({ message: 'Maximum 3 tags allowed per post.', isValidationError: true });
      return;
    }
    setError(null);
    setCurrentChips(prev => [...prev, tagToAdd]);
    setSelectedTagToAdd('');
  };

  const handleConfirm = async () => {
    if (!suggestion) return;
    if (currentChips.length === 0) {
      setError({ message: 'Please keep or select at least one tag before confirming.', isValidationError: true });
      return;
    }

    setConfirming(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/confirm-tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          suggestion_id: suggestion.suggestion_id,
          final_tags: currentChips,
        }),
      });

      const data = await res.json();
      setApiStatus('online');

      if (!res.ok) {
        if (res.status === 409) {
          setError({ message: data.detail || 'This suggestion has already been confirmed.', isConflict: true });
          // Note: leave confirmed state false so duplicate attempt button stays visible for testing edge cases
        } else if (res.status === 422) {
          const detail = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(', ') : data.detail;
          setError({ message: detail || 'Validation error on tags', isValidationError: true });
        } else {
          setError({ message: data.detail || 'Failed to confirm tags.', isNetwork: true });
        }
        return;
      }

      setConfirmed(true);
    } catch (err) {
      setApiStatus('offline');
      setError({ message: 'Failed to submit confirmation. Network error.', isNetwork: true });
    } finally {
      setConfirming(false);
    }
  };

  const availableTagsToAdd = TAG_TAXONOMY.filter(t => !currentChips.includes(t));

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center space-x-2">
            <Edit3 className="w-5 h-5 text-indigo-600" />
            <h2 className="text-lg font-bold text-slate-900">Post Composer</h2>
          </div>
          <span className="bg-indigo-50 text-indigo-600 border border-indigo-100 text-xs font-mono font-semibold px-2.5 py-1 rounded-full">
            Step 1: Input & Tagging
          </span>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSuggest} className="space-y-5">
          <div>
            <label className="block font-mono text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Post Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Building High-Performance Microservices with Go and gRPC"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={loading || (!!suggestion && confirmed)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all text-sm disabled:opacity-60"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="font-mono text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Post Body <span className="text-rose-500">*</span>
              </label>
              <span className="font-mono text-xs text-slate-400">
                {body.length} characters
              </span>
            </div>
            <textarea
              rows={5}
              placeholder="Provide the article or post body content here..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
              disabled={loading || (!!suggestion && confirmed)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all text-sm disabled:opacity-60 resize-none"
            />
          </div>

          {!suggestion && (
            <button
              type="submit"
              disabled={loading || !title.trim() || !body.trim()}
              className="w-full sm:w-auto px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white font-medium rounded-xl shadow-sm transition-all flex items-center justify-center space-x-2 text-sm cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Requesting AI Tags...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Get AI Suggestions</span>
                </>
              )}
            </button>
          )}
        </form>

        {/* Error Notification Surface */}
        {error && (
          <div className={`p-4 rounded-xl text-sm flex items-start justify-between border ${
            error.isConflict 
              ? 'bg-amber-50 border-amber-200 text-amber-900' 
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}>
            <div className="flex items-start space-x-3">
              <AlertCircle className={`w-5 h-5 shrink-0 mt-0.5 ${error.isConflict ? 'text-amber-600' : 'text-rose-600'}`} />
              <div>
                <p className="font-semibold">{error.isConflict ? 'Conflict (HTTP 409)' : 'Notice'}</p>
                <p className="text-xs mt-1 text-slate-700 font-mono">{error.message}</p>
              </div>
            </div>
            {error.isNetwork && (
              <button
                onClick={handleSuggest}
                className="px-3 py-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 text-xs font-mono font-medium rounded-lg transition-all shrink-0 ml-2 shadow-xs cursor-pointer"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {/* Tag Chips & Confirmation Section */}
        {suggestion && (
          <div className="border-t border-slate-100 pt-6 space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Tag className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Tag Suggestions <span className="font-mono text-xs font-normal text-slate-500">({currentChips.length}/3)</span>
                </h3>
              </div>
              {suggestion.was_fallback && (
                <span className="bg-amber-50 text-amber-700 border border-amber-200 text-xs font-mono font-medium px-2.5 py-0.5 rounded-full">
                  Fallback Default Used
                </span>
              )}
            </div>

            {/* Chips Container */}
            <div className="flex flex-wrap items-center gap-2 min-h-[48px] p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              {currentChips.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-medium rounded-lg shadow-2xs"
                >
                  <span>{tag}</span>
                  {!confirmed && (
                    <button
                      type="button"
                      onClick={() => handleRemoveChip(tag)}
                      className="text-slate-400 hover:text-rose-600 transition-colors p-0.5 rounded cursor-pointer"
                      title="Remove tag"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </span>
              ))}

              {currentChips.length === 0 && (
                <span className="text-xs text-slate-400 font-mono italic">No tags selected. Add at least one tag from dropdown below.</span>
              )}
            </div>

            {/* Add Tag Dropdown Control */}
            {!confirmed && (
              <div className="flex items-center space-x-3">
                {currentChips.length < 3 ? (
                  <select
                    value={selectedTagToAdd}
                    onChange={(e) => {
                      const val = e.target.value;
                      setSelectedTagToAdd(val);
                      if (val) handleAddTag(val);
                    }}
                    className="bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 shadow-2xs cursor-pointer"
                  >
                    <option value="">+ Add Tag from Taxonomy...</option>
                    {availableTagsToAdd.map((tag) => (
                      <option key={tag} value={tag}>
                        {tag}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="text-xs font-mono text-slate-400 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
                    Maximum 3 tags reached (dropdown disabled)
                  </span>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="pt-2 flex items-center justify-between">
              {confirmed ? (
                <div className="w-full flex items-center justify-between bg-emerald-50 border border-emerald-200 p-4 rounded-xl">
                  <div className="flex items-center space-x-2 text-emerald-800 text-sm font-medium">
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                    <span>Tags confirmed successfully!</span>
                  </div>
                  <button
                    onClick={() => {
                      setTitle('');
                      setBody('');
                      setSuggestion(null);
                      setCurrentChips([]);
                      setConfirmed(false);
                      setError(null);
                    }}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg shadow-2xs transition-all cursor-pointer"
                  >
                    Create Another Post
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleConfirm}
                    disabled={confirming || currentChips.length === 0}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white font-medium rounded-xl text-sm transition-all flex items-center space-x-2 shadow-sm cursor-pointer disabled:cursor-not-allowed"
                  >
                    {confirming ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4" />
                    )}
                    <span>Confirm Tags</span>
                  </button>

                  <button
                    onClick={() => {
                      setSuggestion(null);
                      setCurrentChips([]);
                      setError(null);
                    }}
                    className="px-4 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl text-sm shadow-2xs transition-all cursor-pointer"
                  >
                    Discard
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// View 2: Metrics Component (Light Mode Restyled)
// ---------------------------------------------------------------------------
function MetricsView({ setApiStatus }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/metrics`);
      setApiStatus('online');
      if (!res.ok) {
        throw new Error(`Metrics request failed with status ${res.status}`);
      }
      const data = await res.json();
      setMetrics(data);
    } catch (err) {
      setApiStatus('offline');
      setError(err.message || 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  if (loading && !metrics) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
        <p className="text-sm font-mono">Loading Pipeline Metrics...</p>
      </div>
    );
  }

  if (error && !metrics) {
    return (
      <div className="max-w-2xl mx-auto p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-900 text-center space-y-4 shadow-sm">
        <AlertCircle className="w-8 h-8 mx-auto text-rose-600" />
        <div>
          <h3 className="font-bold text-base">Unable to Load Metrics</h3>
          <p className="text-xs font-mono text-slate-600 mt-1">{error}</p>
        </div>
        <button
          onClick={fetchMetrics}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-medium transition-all cursor-pointer"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const {
    total_suggestions = 0,
    total_corrections = 0,
    agreement_rate = 0,
    per_tag_stats = {},
    top_tags_added = [],
    top_tags_removed = [],
    daily_trend = [],
  } = metrics || {};

  const agreementPct = (agreement_rate * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Metrics Header & Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Pipeline Performance Metrics</h2>
          <p className="text-xs text-slate-500 font-mono">Real-time aggregate feedback data</p>
        </div>

        <button
          onClick={fetchMetrics}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-mono font-medium rounded-xl transition-all shadow-2xs cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <p className="font-mono text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Suggestions</p>
          <p className="text-3xl font-bold text-slate-900 mt-2">{total_suggestions}</p>
          <p className="text-[11px] font-mono text-slate-400 mt-1">Generated by Groq LLM</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <p className="font-mono text-xs text-slate-500 font-semibold uppercase tracking-wider">Human Corrections</p>
          <p className="text-3xl font-bold text-slate-900 mt-2">{total_corrections}</p>
          <p className="text-[11px] font-mono text-slate-400 mt-1">Confirmed by reviewers</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <p className="font-mono text-xs text-slate-500 font-semibold uppercase tracking-wider">Agreement Rate</p>
          <p className="text-3xl font-bold text-emerald-600 mt-2">{agreementPct}%</p>
          <p className="text-[11px] font-mono text-slate-400 mt-1">Unchanged approvals</p>
        </div>
      </div>

      {/* Top Added / Top Removed Tags Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h3 className="text-xs font-mono font-semibold uppercase text-slate-700 tracking-wider mb-3 flex items-center space-x-2">
            <Plus className="w-4 h-4 text-emerald-600" />
            <span>Most Commonly Added Tags</span>
          </h3>
          {top_tags_added.length === 0 ? (
            <p className="text-xs text-slate-400 font-mono italic">No tags added in corrections yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {top_tags_added.map(tag => (
                <span key={tag} className="px-3 py-1 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-lg font-medium">
                  + {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h3 className="text-xs font-mono font-semibold uppercase text-slate-700 tracking-wider mb-3 flex items-center space-x-2">
            <X className="w-4 h-4 text-rose-600" />
            <span>Most Commonly Removed Tags</span>
          </h3>
          {top_tags_removed.length === 0 ? (
            <p className="text-xs text-slate-400 font-mono italic">No tags removed in corrections yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {top_tags_removed.map(tag => (
                <span key={tag} className="px-3 py-1 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg font-medium">
                  - {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Per-Tag Stats Table */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900">Per-Tag Performance Breakdown</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider font-semibold">
                <th className="py-3 px-4">Taxonomy Tag</th>
                <th className="py-3 px-4 text-right">Times Suggested</th>
                <th className="py-3 px-4 text-right">Times Survived</th>
                <th className="py-3 px-4 text-right">Survival Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {TAG_TAXONOMY.map(tag => {
                const stats = per_tag_stats[tag] || { times_suggested: 0, times_survived: 0 };
                const rate = stats.times_suggested > 0 
                  ? ((stats.times_survived / stats.times_suggested) * 100).toFixed(1) + '%'
                  : 'N/A';

                return (
                  <tr key={tag} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-medium flex items-center space-x-2">
                      <Tag className="w-3.5 h-3.5 text-indigo-600" />
                      <span className="font-semibold text-slate-900">{tag}</span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-slate-600">{stats.times_suggested}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-600">{stats.times_survived}</td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-emerald-600">{rate}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Daily Performance Trend (Over Time) */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900">Daily Performance Trend (Over Time)</h3>

        {(!daily_trend || daily_trend.length === 0) ? (
          <p className="text-xs text-slate-400 font-mono italic">No trend data recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Suggestions</th>
                  <th className="py-3 px-4 text-right">Corrections</th>
                  <th className="py-3 px-4 text-right">Agreement Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {daily_trend.map(entry => {
                  const ratePct = (entry.agreement_rate * 100).toFixed(1) + '%';
                  return (
                    <tr key={entry.date} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 font-mono font-semibold text-slate-900">{entry.date}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-600">{entry.suggestions}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-600">{entry.corrections}</td>
                      <td className="py-3 px-4 text-right font-mono font-semibold text-emerald-600">{ratePct}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

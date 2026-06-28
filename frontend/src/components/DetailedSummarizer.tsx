import { useEffect, useId, useRef, useState, type ChangeEvent } from 'react';
import styles from './DetailedSummarizer.module.css';
import { apiClient } from '../utils/api';
import { renderMarkdown } from '../utils/markdown';

interface SummarySection {
  heading?: string;
  items?: string[];
}

interface SummaryResult {
  topic?: string;
  title?: string;
  timestamp?: string;
  summary?: string;
  content?: string;
  sections?: SummarySection[];
  chunks_used?: number;
  tokens_used?: number;
}

interface FormState {
  topic: string;
  resultsCount: string;
  userId: string;
  chatId: string;
}

export default function DetailedSummarizer() {
  const [formData, setFormData] = useState<FormState>({
    topic: '',
    resultsCount: '5',
    userId: '1',
    chatId: '',
  });

  const [results, setResults] = useState<SummaryResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());
  const [errorMessage, setErrorMessage] = useState('');
  const resultsRef = useRef<HTMLDivElement | null>(null);
  const mountedRef = useRef(true);
  const errorId = useId();

  useEffect(() => {
    return () => { mountedRef.current = false; };
  }, []);

  const handleInputChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { id, value } = e.target;
    setFormData((prev) => ({ ...prev, [id]: value }));
  };

  const summarizeChats = async () => {
    const userId = parseInt(formData.userId);
    if (!userId) {
      setErrorMessage('Please enter a valid User ID.');
      return;
    }

    setErrorMessage('');
    setIsLoading(true);
    try {
      const payload: { topic_name: string; chat_id?: number; n_results: number; max_tokens: number } = {
        topic_name: formData.topic || 'General',
        n_results: parseInt(formData.resultsCount),
        max_tokens: 2000,
      };
      if (formData.chatId) {
        payload.chat_id = parseInt(formData.chatId);
      }

      const startRes = await apiClient.post<{ task_id: string }>(
        `/chats/summary-task?user_id=${userId}`,
        payload,
        { timeoutMs: 30_000 },
      );
      if (startRes.error) throw new Error(startRes.error);
      const taskId = startRes.data!.task_id;

      while (mountedRef.current) {
        await new Promise((r) => setTimeout(r, 2000));
        if (!mountedRef.current) return;
        const pollRes = await apiClient.get<{ status: string; result?: SummaryResult; error?: string }>(
          `/chats/summary-task/${taskId}`,
          { timeoutMs: 30_000 },
        );
        if (pollRes.error) throw new Error(pollRes.error);
        const taskData = pollRes.data!;

        if (taskData.status === 'done') {
          if (mountedRef.current) {
            setResults(taskData.result ? [taskData.result] : []);
            setShowResults(true);
            setExpandedCards(new Set());
            setTimeout(() => {
              resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
          }
          return;
        }
        if (taskData.status === 'error') {
          throw new Error(taskData.error || 'Summary generation failed');
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      setErrorMessage(`Error fetching summaries: ${message}`);
      setShowResults(false);
    } finally {
      setIsLoading(false);
    }
  };

  const clearResults = () => {
    setShowResults(false);
    setResults([]);
    setErrorMessage('');
    setFormData((prev) => ({ ...prev, topic: '', chatId: '' }));
    setExpandedCards(new Set());
  };

  const toggleExpand = (index: number) => {
    setExpandedCards((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <main className={styles.container} aria-labelledby="summarizer-title">
      <div className={styles.header}>
        <h1 id="summarizer-title" className={styles.title}>Detailed Summarizer</h1>
        <p className={styles.subtitle}>
          Extract and refine summaries from your chat history by topic. Discover patterns, key insights, and knowledge at a glance.
        </p>
      </div>

      {errorMessage && (
        <div id={errorId} role="alert" className={styles.emptyState} style={{ borderColor: 'var(--color-danger)' }}>
          <p className={styles.emptyStateText}>{errorMessage}</p>
        </div>
      )}

      <div className={styles.controls}>
        <div className={styles.controlGroup}>
          <label htmlFor="topic" className={styles.label}>Topic</label>
          <input
            type="text"
            id="topic"
            placeholder="e.g., Machine Learning, API Design..."
            value={formData.topic}
            onChange={handleInputChange}
            className={styles.input}
            aria-describedby={errorMessage ? errorId : undefined}
          />
        </div>
        <div className={styles.controlGroup}>
          <label htmlFor="resultsCount" className={styles.label}>Results Count</label>
          <select
            id="resultsCount"
            value={formData.resultsCount}
            onChange={handleInputChange}
            className={styles.select}
          >
            <option value="3">3 Results</option>
            <option value="5">5 Results</option>
            <option value="10">10 Results</option>
            <option value="20">20 Results</option>
          </select>
        </div>
      </div>

      <div className={styles.controls}>
        <div className={styles.controlGroup}>
          <label htmlFor="userId" className={styles.label}>User ID</label>
          <input
            type="number"
            id="userId"
            placeholder="1"
            value={formData.userId}
            onChange={handleInputChange}
            className={styles.input}
            min={1}
            aria-invalid={errorMessage ? true : undefined}
            aria-describedby={errorMessage ? errorId : undefined}
          />
        </div>
        <div className={styles.controlGroup}>
          <label htmlFor="chatId" className={styles.label}>Chat ID (Optional)</label>
          <input
            type="number"
            id="chatId"
            placeholder="Leave empty for all chats"
            value={formData.chatId}
            onChange={handleInputChange}
            className={styles.input}
            min={1}
          />
        </div>
      </div>

      <div className={styles.buttonGroup}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnPrimary}`}
          onClick={summarizeChats}
          disabled={isLoading}
          aria-busy={isLoading}
        >
          {isLoading ? (
            <>
              <span className={styles.loadingSpinner} aria-hidden="true"></span>
              <span>Processing…</span>
            </>
          ) : (
            'Generate Summary'
          )}
        </button>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnSecondary}`}
          onClick={clearResults}
          disabled={isLoading}
        >
          Clear Results
        </button>
      </div>

      {showResults && (
        <section
          className={styles.resultsContainer}
          ref={resultsRef}
          aria-live="polite"
          aria-labelledby="summary-results-title"
        >
          <div className={styles.resultsHeader}>
            <h2 id="summary-results-title" className={styles.resultsTitle}>Summary Results</h2>
            <div className={styles.resultCount}>
              {results.length} {results.length === 1 ? 'result' : 'results'}
            </div>
          </div>

          {results.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyStateIcon} aria-hidden="true">📚</div>
              <h3 className={styles.emptyStateTitle}>No results found</h3>
              <p className={styles.emptyStateText}>Try adjusting your search criteria.</p>
            </div>
          ) : (
            <div className={styles.resultsGrid}>
              {results.map((result, idx) => (
                <article
                  key={idx}
                  className={`${styles.resultCard} ${expandedCards.has(idx) ? styles.expanded : ''}`}
                  style={{ animationDelay: `${0.4 + idx * 0.1}s` }}
                >
                  <div className={styles.cardHeader}>
                    <span className={styles.cardTopic}>{result.topic || 'General'}</span>
                    <h3 className={styles.cardTitle}>{result.title || 'Untitled Summary'}</h3>
                    <div className={styles.cardMeta}>
                      {result.timestamp ? new Date(result.timestamp).toLocaleDateString() : 'Date unknown'}
                    </div>
                  </div>

                  <div className={styles.cardContent}>
                    {result.sections?.length ? (
                      result.sections.map((section, sectionIdx) => (
                        <div key={sectionIdx} className={styles.summarySection}>
                          <h4 className={styles.sectionTitle}>{section.heading}</h4>
                          <ul className={styles.sectionList}>
                            {section.items?.map((item, itemIdx) => <li key={itemIdx}>{item}</li>)}
                          </ul>
                        </div>
                      ))
                    ) : (
                      <div
                        // Markdown sanitized by DOMPurify in renderMarkdown.
                        dangerouslySetInnerHTML={{
                          __html: renderMarkdown(result.summary || result.content || 'No content available'),
                        }}
                      />
                    )}
                  </div>

                  <div className={styles.cardFooter}>
                    <span className={styles.tokenUsage}>
                      {result.chunks_used ?? result.tokens_used ?? '—'} chunks
                    </span>
                    <button
                      type="button"
                      className={styles.expandBtn}
                      onClick={() => toggleExpand(idx)}
                      aria-expanded={expandedCards.has(idx)}
                    >
                      {expandedCards.has(idx) ? 'Collapse' : 'Expand'}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {!showResults && (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon} aria-hidden="true">📚</div>
          <h3 className={styles.emptyStateTitle}>No results yet</h3>
          <p className={styles.emptyStateText}>
            Configure your search criteria and click "Generate Summary" to extract insights from your chats.
          </p>
        </div>
      )}
    </main>
  );
}

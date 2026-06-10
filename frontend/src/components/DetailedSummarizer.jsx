import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import styles from './DetailedSummarizer.module.css';
import { apiClient } from '/src/utils/api';

export default function DetailedSummarizer() {
  const [formData, setFormData] = useState({
    topic: '',
    resultsCount: '5',
    userId: '1',
    chatId: '',
  });

  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [expandedCards, setExpandedCards] = useState(new Set());
  const resultsRef = useRef(null);

  // use centralized apiClient which includes auth headers

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [id]: value
    }));
  };

  const summarizeChats = async () => {
    const userId = parseInt(formData.userId);
    if (!userId) {
      alert('Please enter a valid User ID');
      return;
    }

    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        user_id: userId,
        n_results: parseInt(formData.resultsCount),
        max_tokens: 2000
      });

      const payload = {
        topic_name: formData.topic || 'General',
      };

      if (formData.chatId) {
        payload.chat_id = parseInt(formData.chatId);
      }

      const res = await apiClient.post(`/chats/detailed-summarizer?${params}`, payload);

      if (res.error) {
        throw new Error(res.error);
      }

      setResults([res.data]);
      setShowResults(true);
      setExpandedCards(new Set());

      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (error) {
      console.error('Error:', error);
      alert('Error fetching summaries: ' + error.message);
      setShowResults(false);
    } finally {
      setIsLoading(false);
    }
  };

  const clearResults = () => {
    setShowResults(false);
    setResults([]);
    setFormData(prev => ({
      ...prev,
      topic: '',
      chatId: ''
    }));
    setExpandedCards(new Set());
  };

  const toggleExpand = (index) => {
    const newExpanded = new Set(expandedCards);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedCards(newExpanded);
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Detailed Summarizer</h1>
        <p className={styles.subtitle}>
          Extract and refine summaries from your chat history by topic. Discover patterns, key insights, and knowledge at a glance.
        </p>
      </div>

      {/* Controls */}
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
          />
        </div>
      </div>

      {/* Button Group */}
      <div className={styles.buttonGroup}>
        <button
          className={`${styles.btn} ${styles.btnPrimary}`}
          onClick={summarizeChats}
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className={styles.loadingSpinner}></span>
              <span>Processing...</span>
            </>
          ) : (
            'Generate Summary'
          )}
        </button>
        <button
          className={`${styles.btn} ${styles.btnSecondary}`}
          onClick={clearResults}
          disabled={isLoading}
        >
          Clear Results
        </button>
      </div>

      {/* Results Container */}
      {showResults && (
        <div className={styles.resultsContainer} ref={resultsRef}>
          <div className={styles.resultsHeader}>
            <h2 className={styles.resultsTitle}>Summary Results</h2>
            <div className={styles.resultCount}>
              {results.length} {results.length === 1 ? 'result' : 'results'}
            </div>
          </div>

          {results.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyStateIcon}>📚</div>
              <h3 className={styles.emptyStateTitle}>No results found</h3>
              <p className={styles.emptyStateText}>Try adjusting your search criteria.</p>
            </div>
          ) : (
            <div className={styles.resultsGrid}>
              {results.map((result, idx) => (
                <div
                  key={idx}
                  className={`${styles.resultCard} ${expandedCards.has(idx) ? styles.expanded : ''}`}
                  style={{ animationDelay: `${0.4 + idx * 0.1}s` }}
                >
                  <div className={styles.cardHeader}>
                    <span className={styles.cardTopic}>{result.topic || 'General'}</span>
                    <h3 className={styles.cardTitle}>{result.title || 'Untitled Summary'}</h3>
                    <div className={styles.cardMeta}>
                      {result.timestamp
                        ? new Date(result.timestamp).toLocaleDateString()
                        : 'Date unknown'}
                    </div>
                  </div>

                  <div className={styles.cardContent}>
                    {result.sections?.length ? (
                      result.sections.map((section, sectionIdx) => (
                        <div key={sectionIdx} className={styles.summarySection}>
                          <h4 className={styles.sectionTitle}>{section.heading}</h4>
                          <ul className={styles.sectionList}>
                            {section.items?.map((item, itemIdx) => (
                              <li key={itemIdx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      ))
                    ) : (
                      <ReactMarkdown>{result.summary || result.content || 'No content available'}</ReactMarkdown>
                    )}
                  </div>

                  <div className={styles.cardFooter}>
                    <span className={styles.tokenUsage}>
                      {result.chunks_used || result.tokens_used || '—'} chunks
                    </span>
                    <button
                      className={styles.expandBtn}
                      onClick={() => toggleExpand(idx)}
                    >
                      {expandedCards.has(idx) ? 'Collapse' : 'Expand'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!showResults && (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>📚</div>
          <h3 className={styles.emptyStateTitle}>No results yet</h3>
          <p className={styles.emptyStateText}>
            Configure your search criteria and click "Generate Summary" to extract insights from your chats.
          </p>
        </div>
      )}
    </div>
  );
}

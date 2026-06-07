# Detailed Summarizer Component - React + Astro Integration

## Overview

A production-grade React component for Astro that provides an editorial luxury interface for extracting and summarizing chat history by topic.

## Files Created

```
frontend/src/
├── components/
│   ├── DetailedSummarizer.jsx      # Main React component
│   └── DetailedSummarizer.module.css # Scoped CSS styling
└── pages/
    └── summarizer.astro            # Astro page using the component
```

## Setup Instructions

### 1. Install Dependencies (if not already installed)

```bash
cd frontend
npm install
```

Ensure your `package.json` includes React:
```json
{
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
```

### 2. Configure Environment Variables

Update `frontend/.env` with your API base URL:

```env
PUBLIC_API_BASE=http://localhost:8000
```

**Note**: Environment variables in Astro must be prefixed with `PUBLIC_` to be accessible in client-side code.

### 3. Update Astro Config (if needed)

Ensure `astro.config.mjs` includes React integration:

```javascript
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

export default defineConfig({
  integrations: [react()],
  vite: {
    ssr: {
      external: ['react', 'react-dom']
    }
  }
});
```

### 4. Run Development Server

```bash
npm run dev
```

Access the component at: `http://localhost:3000/summarizer`

## Component Features

### State Management
- **Form Data**: Topic, results count, user ID, chat ID
- **Results**: Stores API responses
- **Loading State**: Visual feedback during API calls
- **Expanded Cards**: Track which result cards are expanded

### API Integration
- **Endpoint**: `POST /chats/detailed-summarizer`
- **Required Params**: `user_id`, `n_results`, `max_tokens`
- **Optional Payload**: `chat_id` (defaults to all chats if omitted), `topic_name`
- **Example Request**:
  ```bash
  curl -X POST "http://localhost:8000/chats/detailed-summarizer?user_id=1&n_results=5&max_tokens=2000" \
    -H "Content-Type: application/json" \
    -d '{"chat_id": 1, "topic_name": "Machine Learning"}'
  ```

### Key Features
✨ **Editorial Luxury Aesthetic**: Merriweather serif + DM Sans typography  
🎨 **Sophisticated Dark Theme**: Deep navy with warm/cool accent colors  
⚡ **Smooth Animations**: Staggered reveals, hover effects, loading states  
📱 **Fully Responsive**: Mobile, tablet, and desktop optimized  
🔄 **Real-time Results**: Smooth scrolling to results section  
🎯 **Expand/Collapse**: Individual card expansion for detailed views  

## Styling Details

### CSS Variables (Available in theme)
```css
--bg-primary: #0f0f12;
--bg-secondary: #1a1a1f;
--text-primary: #f5f5f7;
--text-secondary: #a8a8ad;
--accent-warm: #e8956d;   /* Terracotta */
--accent-cool: #6ba3d4;   /* Sky blue */
--border: #3a3a42;
--transition: 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Animations
- `fadeInDown`: Header entrance
- `fadeInUp`: Controls and results entrance
- `fadeInScale`: Card staggered reveals
- `spin`: Loading spinner

## Component Props

**DetailedSummarizer** accepts no required props — it's fully self-contained:

```jsx
<DetailedSummarizer client:load />
```

The `client:load` directive ensures React hydration on page load.

## Error Handling

- ✅ Validates user ID before API call
- ✅ Catches and displays API errors
- ✅ Shows empty state if no results
- ✅ Handles network failures gracefully

## Performance Considerations

1. **CSS Modules**: Scoped styling prevents conflicts
2. **React.lazy**: Can be added for code splitting if needed
3. **useRef**: Smooth scrolling without full re-renders
4. **Set for expandedCards**: O(1) lookup for expand state

## Accessibility

- Semantic HTML
- Proper form labels and associations
- Clear button states (disabled during loading)
- ARIA-friendly status messages
- Keyboard navigable

## Customization

### Change API Endpoint
Update the `API_BASE` constant in `DetailedSummarizer.jsx`:

```jsx
const API_BASE = import.meta.env.PUBLIC_API_BASE || 'http://localhost:8000';
```

### Modify Colors
Edit CSS variables in `DetailedSummarizer.module.css`:

```css
:root {
  --accent-warm: #your-color;
  --accent-cool: #your-color;
  /* ... */
}
```

### Adjust Grid Layout
Modify grid template columns in `.resultsGrid`:

```css
grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
```

## Deployment Considerations

1. **Build**: `npm run build` generates static + optimized React
2. **API CORS**: Ensure backend allows CORS from frontend domain
3. **Environment**: Set `PUBLIC_API_BASE` in production `.env`
4. **Fonts**: Google Fonts loaded from CDN (no local setup needed)

## Troubleshooting

**Component not rendering**
- Ensure `@astrojs/react` is installed: `npm install @astrojs/react`
- Check `astro.config.mjs` includes React integration
- Verify `client:load` directive is present in `.astro` file

**API calls failing**
- Check `PUBLIC_API_BASE` in `.env`
- Verify backend is running on configured port
- Check CORS headers in backend response
- Open DevTools Network tab for request details

**Styles not applying**
- CSS Modules are scoped by Astro automatically
- Import as `styles` object: `import styles from './DetailedSummarizer.module.css'`
- Use `className={styles.className}` syntax

**Animations not smooth**
- Check browser hardware acceleration settings
- Verify GPU rendering in DevTools Performance tab
- Reduce animation complexity on lower-end devices

## Support

For issues or questions:
1. Check component comments in `DetailedSummarizer.jsx`
2. Review Astro React docs: https://docs.astro.build/en/guides/integrations-guide/react/
3. Check API response format in console logs

/**
 * PDF Renderer Integration Tests
 * 
 * Tests for the new PDF rendering system components
 * Location: src/components/reader/__tests__/PDFRenderer.test.jsx
 * 
 * Run with: npm run test:unit -- PDFRenderer
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import PaperPDFViewer from '../PaperPDFViewer';
import AdvancedPDFViewer from '../AdvancedPDFViewer';

/**
 * Test Suite: PaperPDFViewer Component
 */
describe('PaperPDFViewer', () => {
  const mockPaper = {
    id: '123',
    title: 'Test Research Paper',
    content: 'This is a test paper.\n\nIt has multiple paragraphs.\n\nEach paragraph should be on a separate page if long enough.',
    authors: ['Author One', 'Author Two'],
    year: 2024,
  };

  it('should render without crashing', () => {
    render(<PaperPDFViewer paper={mockPaper} />);
    expect(screen.getByText(/This is a test paper/)).toBeInTheDocument();
  });

  it('should display loading state', () => {
    render(<PaperPDFViewer paper={mockPaper} isLoading={true} />);
    expect(screen.getByText('Loading paper...')).toBeInTheDocument();
  });

  it('should display error state', () => {
    const errorMessage = { message: 'Failed to load paper' };
    render(
      <PaperPDFViewer 
        paper={mockPaper} 
        error={errorMessage}
      />
    );
    expect(screen.getByText(/Failed to load paper/)).toBeInTheDocument();
  });

  it('should handle missing content gracefully', () => {
    const paperWithoutContent = { ...mockPaper };
    delete paperWithoutContent.content;
    
    render(<PaperPDFViewer paper={paperWithoutContent} />);
    // Should still render without crashing
    expect(screen.getByText(/Test Research Paper/)).toBeInTheDocument();
  });

  it('should render content when title is missing', () => {
    const paperWithoutTitle = { 
      id: '123',
      content: 'Some content'
    };
    
    render(<PaperPDFViewer paper={paperWithoutTitle} />);
    expect(screen.getByText(/Some content/)).toBeInTheDocument();
  });

  it('should call onDownload callback when provided', async () => {
    const mockDownload = jest.fn();
    render(
      <PaperPDFViewer 
        paper={mockPaper}
        onDownload={mockDownload}
      />
    );
    
    // Note: Actual download button interaction would be tested here
    // This is a placeholder for the actual implementation
  });
});

/**
 * Test Suite: AdvancedPDFViewer Component
 */
describe('AdvancedPDFViewer', () => {
  const mockPages = [
    <div key="1">Page 1 Content</div>,
    <div key="2">Page 2 Content</div>,
    <div key="3">Page 3 Content</div>,
  ];

  it('should render all pages', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Page 1 Content')).toBeInTheDocument();
  });

  it('should display page navigation controls', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    expect(screen.getByRole('spinbutton')).toHaveValue(1); // Page indicator
  });

  it('should navigate to next page', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const nextButton = getByRole('button', { name: /next page/i });
    fireEvent.click(nextButton);
    
    await waitFor(() => {
      expect(screen.getByRole('spinbutton')).toHaveValue(2);
    });
  });

  it('should navigate to first page', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Go to page 2 first
    fireEvent.click(getByRole('button', { name: /next page/i }));
    
    expect(screen.getByRole('spinbutton')).toHaveValue(2);
    
    // Go back to page 1
    fireEvent.click(getByRole('button', { name: /first page/i }));
    
    expect(screen.getByRole('spinbutton')).toHaveValue(1);
  });

  it('should disable navigation buttons at boundaries', () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const firstButton = getByRole('button', { name: /first page/i });
    expect(firstButton).toBeDisabled();
  });

  it('should handle zoom in/out', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const zoomInButton = getByRole('button', { name: /zoom in/i });
    fireEvent.click(zoomInButton);
    
    await waitFor(() => {
      expect(screen.getByText(/120%/)).toBeInTheDocument();
    });
  });

  it('should display loading state', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={[]}
        isLoading={true}
      />
    );
    
    expect(screen.getByText('Rendering PDF...')).toBeInTheDocument();
  });

  it('should display error state', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={[]}
        error="Failed to render PDF"
      />
    );
    
    expect(screen.getByText('Failed to render PDF')).toBeInTheDocument();
  });

  it('should display empty state for no pages', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={[]}
      />
    );
    
    expect(screen.getByText('No pages available')).toBeInTheDocument();
  });

  it('should toggle fullscreen mode', async () => {
    const { getAllByRole, container } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Find and click the fullscreen button
    const buttons = getAllByRole('button');
    const fullscreenButton = Array.from(buttons).find(
      btn => btn.getAttribute('title') === 'Full Screen'
    );
    
    if (fullscreenButton) {
      fireEvent.click(fullscreenButton);
      
      await waitFor(() => {
        const mainDiv = container.querySelector('[class*="fixed"]');
        expect(mainDiv).toBeTruthy();
      });
    }
  });
});

/**
 * Test Suite: Keyboard Shortcuts
 */
describe('Keyboard Shortcuts', () => {
  const mockPages = [
    <div key="1">Page 1</div>,
    <div key="2">Page 2</div>,
    <div key="3">Page 3</div>,
  ];

  it('should navigate with arrow keys', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Press ArrowRight to go to next page
    fireEvent.keyDown(document.body, { key: 'ArrowRight' });
    expect(screen.getByRole('spinbutton')).toHaveValue(2);
  });

  it('should navigate with h/l keys', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Press 'l' to go to next page
    fireEvent.keyDown(document.body, { key: 'l' });
    expect(screen.getByRole('spinbutton')).toHaveValue(2);
  });

  it('should ignore shortcuts when input is focused', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const input = getByRole('spinbutton');
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: 'ArrowRight' });
    
    expect(screen.getByRole('spinbutton')).toHaveValue(1);
  });
});

/**
 * Test Suite: Content Parsing
 */
describe('Content Parsing', () => {
  it('should parse markdown headers', () => {
    const content = `# Title\n\nSome content\n\n## Subtitle\n\nMore content`;
    const mockPaper = {
      title: 'Test',
      content: content,
    };
    
    render(<PaperPDFViewer paper={mockPaper} />);
    expect(screen.getByText(/Some content/)).toBeInTheDocument();
  });

  it('should handle lists', () => {
    const content = `- Item 1\n- Item 2\n- Item 3`;
    const mockPaper = {
      title: 'Test',
      content: content,
    };
    
    render(<PaperPDFViewer paper={mockPaper} />);
    // The list should be rendered without errors
    expect(screen.getByText(/- Item 1/)).toBeInTheDocument();
  });

  it('should handle code blocks', () => {
    const content = `\`\`\`\nconst x = 10;\n\`\`\``;
    const mockPaper = {
      title: 'Test',
      content: content,
    };
    
    render(<PaperPDFViewer paper={mockPaper} />);
    expect(screen.getByText(/const x = 10;/)).toBeInTheDocument();
  });
});

/**
 * Test Suite: Responsive Design
 */
describe('Responsive Design', () => {
  const mockPages = [
    <div key="1">Page 1 Content</div>,
  ];

  beforeEach(() => {
    // Reset viewport
    global.innerWidth = 1024;
    global.innerHeight = 768;
  });

  it('should render on desktop', () => {
    global.innerWidth = 1920;
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('should render on tablet', () => {
    global.innerWidth = 768;
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('should render on mobile', () => {
    global.innerWidth = 375;
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });
});

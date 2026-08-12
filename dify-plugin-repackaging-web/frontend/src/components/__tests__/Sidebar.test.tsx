import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../test/utils/test-utils';
import useAppStore from '../../stores/appStore';

vi.mock('../CompletedFiles', () => ({
  default: () => <div>Completed files content</div>,
}));

import Sidebar from '../Sidebar';

describe('Sidebar', () => {
  beforeEach(() => {
    useAppStore.setState({ isSidebarOpen: true });
  });

  it('renders completed files above the sticky application header', () => {
    render(<Sidebar />);

    expect(screen.getByTestId('completed-files-sidebar')).toHaveClass('z-[55]');
    expect(screen.getByRole('button', { name: 'Close sidebar' })).toHaveClass('z-[56]');
    expect(screen.getByTestId('sidebar-mobile-overlay')).toHaveClass('z-[54]');
  });
});

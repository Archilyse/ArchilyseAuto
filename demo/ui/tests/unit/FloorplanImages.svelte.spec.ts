import '@testing-library/jest-dom';
import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import FloorplanImages from '../../src/components/FloorplanImages.svelte';
import { UploadStatus } from '../../src/types';
import { processedBackground, processedIcons, processedSpaces, processedWalls } from '../../src/stores';


describe('FloorplanImages component', () => {
    const MOCK_ORIGINAL_SRC = 'src-to-original-image';
    const MOCK_WALLS_SRC = 'src-to-walls-image';
    const MOCK_ICONS_SRC = 'src-to-icons-image';
    const MOCK_SPACES_SRC = 'src-to-spaces-image';
    const MOCK_BACKGROUND_SRC = 'src-to-background-image';

    const assertImg = (screen, expectedImgSrc, altText, options = { blurred: false }) => {
        const image = screen.getByAltText(new RegExp(altText));
        expect(image).toBeInTheDocument();
        expect(image).toHaveAttribute('src', expectedImgSrc);
        if (options.blurred) {
            expect(image).toHaveClass('blur');
        } else {
            expect(image).not.toHaveClass('blur')
        }
    };

    describe('Floorplan images', () => {
        test('Renders original image', () => {
            render(FloorplanImages, { original: MOCK_ORIGINAL_SRC });
            assertImg(screen, MOCK_ORIGINAL_SRC, 'Preview of the uploaded plan');
        });

        test('Renders blurry walls & icons when they are available while loading', () => {
            const props = { original: MOCK_ORIGINAL_SRC, uploadStatus:UploadStatus.LOADING };
            const { rerender } = render(FloorplanImages, props);
            assertImg(screen, MOCK_ORIGINAL_SRC, 'Preview of the uploaded plan');

            // When setting processed walls, it renders the wall image blurred
            processedWalls.set(MOCK_WALLS_SRC);
            rerender(props);
            assertImg(screen, MOCK_WALLS_SRC, 'Processed walls', { blurred: true });

            // When setting processed icons, it renders the icon image blurredy
            processedIcons.set(MOCK_ICONS_SRC);
            rerender(props);
            assertImg(screen, MOCK_ICONS_SRC, 'Processed features', { blurred: true });

            // When setting processed spaces, it renders the spaces image blurredy
            processedSpaces.set(MOCK_SPACES_SRC);
            rerender(props);
            assertImg(screen, MOCK_SPACES_SRC, 'Processed spaces', { blurred: true });

            // When setting processed background, it renders the background image blurred
            processedBackground.set(MOCK_BACKGROUND_SRC);
            rerender(props);
            assertImg(screen, MOCK_BACKGROUND_SRC, 'Processed background', { blurred: true });
        });
        test('Renders walls & icons normally when request finishes', () => {
            processedWalls.set(MOCK_WALLS_SRC);
            processedIcons.set(MOCK_ICONS_SRC);
            processedSpaces.set(MOCK_SPACES_SRC);
            processedBackground.set(MOCK_BACKGROUND_SRC);

            const props = { original: MOCK_ORIGINAL_SRC, uploadStatus:UploadStatus.SUCCESS };
            render(FloorplanImages, props);

            assertImg(screen, MOCK_ORIGINAL_SRC, 'Preview of the uploaded plan');
            assertImg(screen, MOCK_WALLS_SRC, 'Processed walls', { blurred: false });
            assertImg(screen, MOCK_ICONS_SRC, 'Processed features', { blurred: false });
            assertImg(screen, MOCK_SPACES_SRC, 'Processed spaces', { blurred: false });
            assertImg(screen, MOCK_BACKGROUND_SRC, 'Processed background', { blurred: false });
        });
    });


    describe('Upload status', () => {
        test('When loading, renders a loading text with the original image', () => {
            render(FloorplanImages, { original: MOCK_ORIGINAL_SRC, uploadStatus: UploadStatus.LOADING });
            assertImg(screen, MOCK_ORIGINAL_SRC, 'Preview of the uploaded plan');
            expect(screen.getByText('Loading...')).toBeInTheDocument();
        });

        test('No loading text when the upload has finished', () => {
            render(FloorplanImages, { original: MOCK_ORIGINAL_SRC, uploadStatus: UploadStatus.SUCCESS });
            expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
        });
        test('On error, shows an error message', () => {
            render(FloorplanImages, { original: MOCK_ORIGINAL_SRC, uploadStatus: UploadStatus.FAILED });
            expect(screen.getByText(/Error uploading the file/)).toBeInTheDocument();
        });
    });

});

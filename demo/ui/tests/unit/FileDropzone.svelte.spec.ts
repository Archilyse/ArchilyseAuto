import '@testing-library/jest-dom';
import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import FileDropzone from '../../src/components/FileDropzone.svelte';



describe('FileDropzone component', () => {
    test('If is not authenticated, the file input is disabled', () => {
        const {container} = render(FileDropzone, { isAuthenticated: false});
        expect(container.querySelector(`input[name="file-dropzone disabled"]`)).toBeInTheDocument(); // @HACK: Using the name because file-dropzone library does not change the HTML input disabled property, it is controlled by JS
    })
    test('If is authenticated, the file input is not disabled', () => {
        const {container} = render(FileDropzone, { isAuthenticated: true});
        expect(container.querySelector(`input[name="file-dropzone"]`)).toBeInTheDocument();
        expect(container.querySelector(`input[name="file-dropzone disabled"]`)).not.toBeInTheDocument();
    })
});

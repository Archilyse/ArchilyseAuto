import '@testing-library/jest-dom';
import { describe, test, expect } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import FileDropzone from '../../src/components/FileDropzone.svelte';
import { UPLOAD_CONFIG } from "../../src/constants";
import { UploadStatus } from '../../src/types';
const { MAX_FILE_SIZE, OPTIMAL_SCALE, ACCEPTED_FILE_EXTENSIONS } = UPLOAD_CONFIG;
const MAX_SIZE_MB = MAX_FILE_SIZE / 1024 ** 2;


describe('FileDropzone component', () => {
    test('Renders normally without an upload', () => {
        const {container} = render(FileDropzone, { uploadStatus: null});
        expect(container.querySelector(`.file-dropzone`)).toBeInTheDocument();
        expect(container.querySelector(`.file-dropzone.disabled`)).not.toBeInTheDocument();
        expect(container).toHaveTextContent(`Accepted files: ${ACCEPTED_FILE_EXTENSIONS.join(', ').replace(/\./g, '')}`);
        expect(container).toHaveTextContent(`Max size: ${MAX_SIZE_MB}MB`);
        expect(container).toHaveTextContent(`Optimal scale: ${OPTIMAL_SCALE}px/m`);
    })
    test('Renders normally with a failed an upload', () => {
        const {container} = render(FileDropzone, { uploadStatus: UploadStatus.FAILED});
        expect(container.querySelector(`.file-dropzone`)).toBeInTheDocument();
        expect(container.querySelector(`.file-dropzone.disabled`)).not.toBeInTheDocument();
    })
    test('Is disabled with an upload in progress', () => {
        const {container} = render(FileDropzone, { uploadStatus: UploadStatus.LOADING});
        expect(container.querySelector(`.file-dropzone.disabled`)).toBeInTheDocument();
    })
    test('Is disabled with a finished upload', () => {
        const {container} = render(FileDropzone, { uploadStatus: UploadStatus.SUCCESS});
        expect(container.querySelector(`.file-dropzone.disabled`)).toBeInTheDocument();
    })
    test('Displays error message for file larger than the maximum size', () => {
        const {container} = render(FileDropzone, { uploadStatus: null, fileTooLarge: true});
        expect(container.querySelector(`.file-dropzone`)).toBeInTheDocument();
        expect(container.querySelector(`.error-message`)).toHaveTextContent(`File is larger than ${MAX_SIZE_MB}MB, please try again with a smaller file`);
    })
    test('Displays error message for invalid file type', async () => {
        const { container } = render(FileDropzone, { uploadStatus: null });
        const file = new File(['Invalid file type'], 'payaso.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
        const fileInput = container.querySelector('input[type=file]');
        await fireEvent.change(fileInput, { target: { files: [file] } });
        expect(container.querySelector(`.error-message`)).toHaveTextContent(`File type must be one of ${ACCEPTED_FILE_EXTENSIONS.join(', ')}, please try again`);
    })
});

import { useEffect, useState } from "react";

function UploadedDocuments({ documents, onPreview }) {
  const [previewDocument, setPreviewDocument] = useState(null);

  useEffect(() => {
    if (!previewDocument) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === "Escape") setPreviewDocument(null);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [previewDocument]);

  function openPreview(document) {
    setPreviewDocument(document);
    onPreview?.(document);
  }

  return (
    <>
      <section className="employee-review-card" aria-labelledby="documents-title">
        <div className="employee-section-heading"><div><p className="employee-eyebrow">Claim evidence</p><h2 id="documents-title">Uploaded Documents</h2></div><span className="employee-count-pill">{documents.length} files</span></div>
        <ul className="employee-document-list">{documents.map((document) => <li key={document.name}><span className="employee-document-icon" aria-hidden="true">▤</span><div><strong>{document.name}</strong><small>{document.type} · Uploaded {document.uploadDate}</small></div><span className={`employee-document-status ${document.status === "Verified" ? "is-verified" : "needs-attention"}`}>{document.status}</span><button type="button" onClick={() => openPreview(document)}>Preview</button></li>)}</ul>
      </section>
      {previewDocument && (
        <div className="employee-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setPreviewDocument(null)}>
          <section className="employee-modal employee-document-modal" role="dialog" aria-modal="true" aria-labelledby="employee-preview-title">
            <header><div><p className="employee-eyebrow">Document preview</p><h2 id="employee-preview-title">{previewDocument.name}</h2></div><button type="button" className="employee-modal-close" aria-label="Close document preview" onClick={() => setPreviewDocument(null)}>×</button></header>
            <div className="employee-pdf-viewer" aria-label={`Mock PDF preview of ${previewDocument.name}`}>
              <div className="employee-pdf-toolbar"><span>PDF</span><span>Page 1 of 1</span><span>100%</span></div>
              <div className="employee-pdf-page"><span className="employee-pdf-mark">CARE FLOW</span><h3>{previewDocument.type}</h3><p>Claim document preview</p><div /><div /><div className="is-short" /><small>This is a secure mock preview. Connect the document endpoint to display the original PDF.</small></div>
            </div>
            <footer><span>{previewDocument.status}</span><button type="button" onClick={() => setPreviewDocument(null)}>Close Preview</button></footer>
          </section>
        </div>
      )}
    </>
  );
}

export default UploadedDocuments;

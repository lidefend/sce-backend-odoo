export type RecordDeepLinkEvidenceInput = {
  expectedBuildSha: string;
  servedBuildInfo: { sha?: string } | null;
  bundleAssets: Array<{
    resource_url?: string;
    decoded_body_size?: number;
    resource_sha256?: string;
  }>;
};

export function validateRecordDeepLinkEvidence(input: RecordDeepLinkEvidenceInput): string[];

class DataHubAssertionQueries:
    """Hold the exact writes and reads one recorded verdict travels through.

    A rule never sees these. They state how a verdict is declared, reported, remembered, and read
    back, so they belong beside the recording that performs it rather than inside the class.
    """

    upsert = """mutation MCMRUpsertAssertion(
  $assertion: String!
  $entity: String!
  $category: String!
  $description: String!
  $platform: String!
  $externalUrl: String
) {
  upsertCustomAssertion(
    urn: $assertion
    input: {
      entityUrn: $entity
      type: $category
      description: $description
      platform: {name: $platform}
      externalUrl: $externalUrl
    }
  ) {
    urn
  }
}"""

    report = """mutation MCMRReportAssertionResult(
  $assertion: String!
  $timestampMillis: Long!
  $type: AssertionResultType!
  $properties: [StringMapEntryInput!]
  $externalUrl: String
) {
  reportAssertionResult(
    urn: $assertion
    result: {
      timestampMillis: $timestampMillis
      type: $type
      properties: $properties
      externalUrl: $externalUrl
    }
  )
}"""

    link = """mutation MCMRWriteback(
  $urn: String!
  $url: String!
  $label: String!
) {
  addLink(input: {resourceUrn: $urn, linkUrl: $url, label: $label})
}"""

    links = """query MCMRWritebackLinks($urn: String!) {
  dataset(urn: $urn) {
    institutionalMemory {
      elements { url label }
    }
  }
}"""

    timeline = """query MCMRAssertionHistory($urn: String!, $count: Int!) {
  dataset(urn: $urn) {
    assertions(start: 0, count: $count) {
      total
      assertions {
        urn
        info { description externalUrl }
        runEvents(limit: $count) {
          total
          failed
          succeeded
          runEvents {
            timestampMillis
            status
            result { type nativeResults { key value } }
          }
        }
      }
    }
  }
}"""

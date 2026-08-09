class DataHubCatalogQueries:
    """Hold the exact reads one bounded catalog snapshot is built from.

    A rule never sees these. They state which governance a provider projects into facts, so
    they belong beside that projection rather than inside the class performing it.

    Both reads name `DATASET`, and the lineage read has to because the snapshot the rules resolve
    an edge against holds datasets alone. A downstream chart or dashboard would arrive as an
    endpoint that snapshot can never hold, so every such edge would read as broken lineage when
    the only broken thing was asking one read for a vocabulary the other does not speak.
    """

    assets = """query MCMRDataAssets($query: String!, $count: Int!, $start: Int!) {
  searchAcrossEntities(input: {
    query: $query
    count: $count
    start: $start
    types: [DATASET]
    searchFlags: {skipHighlighting: true}
  }) {
    total
    searchResults {
      entity {
        urn
        ... on Dataset {
          properties { description lastModified { time } }
          deprecation { deprecated }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username }
                ... on CorpGroup { urn name }
              }
            }
          }
          domain { domain { urn properties { name } } }
          schemaMetadata {
            fields {
              fieldPath
              type
              description
              globalTags { tags { tag { urn properties { name } } } }
              glossaryTerms { terms { term { urn properties { name } } } }
            }
          }
        }
      }
    }
  }
}"""
    field_lineage = """query MCMRFieldLineage($urn: String!) {
  dataset(urn: $urn) {
    urn
    fineGrainedLineages {
      upstreams { urn path }
      downstreams { urn path }
    }
  }
}"""
    lineage = """query MCMRDataLineage($urn: String!, $count: Int!, $start: Int!) {
  searchAcrossLineage(input: {
    urn: $urn
    direction: DOWNSTREAM
    query: "*"
    types: [DATASET]
    count: $count
    start: $start
    searchFlags: {skipHighlighting: true}
  }) {
    total
    searchResults {
      degree
      entity { urn }
    }
  }
}"""

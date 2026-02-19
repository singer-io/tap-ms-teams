from singer import metadata

def generate_catalog(streams):

    catalog = {}
    catalog['streams'] = []
    for stream in streams:
        schema = stream.load_schema()

        mdata = metadata.new()
        mdata = metadata.get_standard_metadata(
            schema=schema,
            key_properties=getattr(stream, "key_properties"),
            valid_replication_keys=(getattr(stream, "valid_replication_keys") or []),
            replication_method=getattr(stream, "replication_method")
        )
        mdata = metadata.to_map(mdata)

        automatic_keys = getattr(stream, "valid_replication_keys") or []
        for field_name in schema.get("properties", {}).keys():
            if field_name in automatic_keys:
                mdata = metadata.write(
                    mdata, ("properties", field_name), "inclusion", "automatic"
                )

        mdata = metadata.to_list(mdata)

        key_properties = metadata.to_map(mdata).get((), {}).get("table-key-properties")
        catalog_entry = {
            'stream': stream.name,
            'key_properties': key_properties,
            'tap_stream_id': stream.name,
            'schema': schema,
            'metadata': mdata
        }
        catalog['streams'].append(catalog_entry)

    return catalog

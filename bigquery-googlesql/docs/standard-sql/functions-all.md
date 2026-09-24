> [!WARNING]
> GoogleSQL is the new name for Google Standard SQL! New name, same great SQL dialect.

This topic contains all functions supported by GoogleSQL for BigQuery.

## Function list

| Name | Summary |
|---|---|
| [`ABS`](mathematical_functions.md#abs) | Computes the absolute value of `X`. |
| [`ACOS`](mathematical_functions.md#acos) | Computes the inverse cosine of `X`. |
| [`ACOSH`](mathematical_functions.md#acosh) | Computes the inverse hyperbolic cosine of `X`. |
| [`AEAD.DECRYPT_BYTES`](aead_encryption_functions.md#aeaddecrypt_bytes) | Uses the matching key from a keyset to decrypt a `BYTES` ciphertext. |
| [`AEAD.DECRYPT_STRING`](aead_encryption_functions.md#aeaddecrypt_string) | Uses the matching key from a keyset to decrypt a `BYTES` ciphertext into a `STRING` plaintext. |
| [`AEAD.ENCRYPT`](aead_encryption_functions.md#aeadencrypt) | Encrypts `STRING` plaintext, using the primary cryptographic key in a keyset. |
| [`AGG`](aggregate_functions.md#agg) | Aggregates a measure type. |
| [`ANY_VALUE`](aggregate_functions.md#any_value) | Gets an expression for some row. |
| [`APPENDS`](time-series-functions.md#appends) | Returns all rows appended to a table for a given time range. |
| [`APPROX_COUNT_DISTINCT`](approximate_aggregate_functions.md#approx_count_distinct) | Gets the approximate result for `COUNT(DISTINCT expression)`. |
| [`APPROX_QUANTILES`](approximate_aggregate_functions.md#approx_quantiles) | Gets the approximate quantile boundaries. |
| [`APPROX_TOP_COUNT`](approximate_aggregate_functions.md#approx_top_count) | Gets the approximate top elements and their approximate count. |
| [`APPROX_TOP_SUM`](approximate_aggregate_functions.md#approx_top_sum) | Gets the approximate top elements and sum, based on the approximate sum of an assigned weight. |
| [`ARRAY`](array_functions.md#array) | Produces an array with one element for each row in a subquery. |
| [`ARRAY_AGG`](aggregate_functions.md#array_agg) | Gets an array of values. |
| [`ARRAY_CONCAT`](array_functions.md#array_concat) | Concatenates one or more arrays with the same element type into a single array. |
| [`ARRAY_CONCAT_AGG`](aggregate_functions.md#array_concat_agg) | Concatenates arrays and returns a single array as a result. |
| [`ARRAY_FIRST`](array_functions.md#array_first) | Gets the first element in an array. |
| [`ARRAY_LAST`](array_functions.md#array_last) | Gets the last element in an array. |
| [`ARRAY_LENGTH`](array_functions.md#array_length) | Gets the number of elements in an array. |
| [`ARRAY_REVERSE`](array_functions.md#array_reverse) | Reverses the order of elements in an array. |
| [`ARRAY_SLICE`](array_functions.md#array_slice) | Produces an array containing zero or more consecutive elements from an input array. |
| [`ARRAY_TO_STRING`](array_functions.md#array_to_string) | Produces a concatenation of the elements in an array as a `STRING` value. |
| [`ASCII`](string_functions.md#ascii) | Gets the ASCII code for the first character or byte in a `STRING` or `BYTES` value. |
| [`ASIN`](mathematical_functions.md#asin) | Computes the inverse sine of `X`. |
| [`ASINH`](mathematical_functions.md#asinh) | Computes the inverse hyperbolic sine of `X`. |
| [`ATAN`](mathematical_functions.md#atan) | Computes the inverse tangent of `X`. |
| [`ATAN2`](mathematical_functions.md#atan2) | Computes the inverse tangent of `X/Y`, using the signs of `X` and `Y` to determine the quadrant. |
| [`ATANH`](mathematical_functions.md#atanh) | Computes the inverse hyperbolic tangent of `X`. |
| [`AVG`](aggregate_functions.md#avg) | Gets the average of non-`NULL` values. |
| [`AVG` (Differential Privacy)](aggregate-dp-functions.md#dp_avg) | `DIFFERENTIAL_PRIVACY`-supported `AVG`. Gets the differentially-private average of non-`NULL`, non-`NaN` values in a query with a `DIFFERENTIAL_PRIVACY` clause. |
| [`BAG_OF_WORDS`](text-analysis-functions.md#bag_of_words) | Gets the frequency of each term (token) in a tokenized document. |
| [`BIT_AND`](aggregate_functions.md#bit_and) | Performs a bitwise AND operation on an expression. |
| [`BIT_COUNT`](bit_functions.md#bit_count) | Gets the number of bits that are set in an input expression. |
| [`BIT_OR`](aggregate_functions.md#bit_or) | Performs a bitwise OR operation on an expression. |
| [`BIT_XOR`](aggregate_functions.md#bit_xor) | Performs a bitwise XOR operation on an expression. |
| [`BOOL`](json_functions.md#bool_for_json) | Converts a JSON boolean to a SQL `BOOL` value. |
| [`BYTE_LENGTH`](string_functions.md#byte_length) | Gets the number of `BYTES` in a `STRING` or `BYTES` value. |
| [`CAST`](conversion_functions.md#cast) | Convert the results of an expression to the given type. |
| [`CBRT`](mathematical_functions.md#cbrt) | Computes the cube root of `X`. |
| [`CEIL`](mathematical_functions.md#ceil) | Gets the smallest integral value that isn't less than `X`. |
| [`CEILING`](mathematical_functions.md#ceiling) | Synonym of `CEIL`. |
| [`CHANGES`](time-series-functions.md#changes) | Returns all rows that have changed in a table for a given time range. |
| [`CHAR_LENGTH`](string_functions.md#char_length) | Gets the number of characters in a `STRING` value. |
| [`CHARACTER_LENGTH`](string_functions.md#character_length) | Synonym for `CHAR_LENGTH`. |
| [`CHR`](string_functions.md#chr) | Converts a Unicode code point to a character. |
| [`CODE_POINTS_TO_BYTES`](string_functions.md#code_points_to_bytes) | Converts an array of extended ASCII code points to a `BYTES` value. |
| [`CODE_POINTS_TO_STRING`](string_functions.md#code_points_to_string) | Converts an array of extended ASCII code points to a `STRING` value. |
| [`COLLATE`](string_functions.md#collate) | Combines a `STRING` value and a collation specification into a collation specification-supported `STRING` value. |
| [`CONCAT`](string_functions.md#concat) | Concatenates one or more `STRING` or `BYTES` values into a single result. |
| [`CONTAINS_SUBSTR`](string_functions.md#contains_substr) | Performs a normalized, case-insensitive search to see if a value exists as a substring in an expression. |
| [`CORR`](statistical_aggregate_functions.md#corr) | Computes the Pearson coefficient of correlation of a set of number pairs. |
| [`COS`](mathematical_functions.md#cos) | Computes the cosine of `X`. |
| [`COSH`](mathematical_functions.md#cosh) | Computes the hyperbolic cosine of `X`. |
| [`COSINE_DISTANCE`](mathematical_functions.md#cosine_distance) | Computes the cosine distance between two vectors. |
| [`COT`](mathematical_functions.md#cot) | Computes the cotangent of `X`. |
| [`COTH`](mathematical_functions.md#coth) | Computes the hyperbolic cotangent of `X`. |
| [`COUNT`](aggregate_functions.md#count) | Gets the number of rows in the input, or the number of rows with an expression evaluated to any value other than `NULL`. |
| [`COUNT` (Differential Privacy)](aggregate-dp-functions.md#dp_count) | `DIFFERENTIAL_PRIVACY`-supported `COUNT`. Signature 1: Gets the differentially-private count of rows in a query with a `DIFFERENTIAL_PRIVACY` clause. <br /> Signature 2: Gets the differentially-private count of rows with a non-`NULL` expression in a query with a `DIFFERENTIAL_PRIVACY` clause. |
| [`COUNTIF`](aggregate_functions.md#countif) | Gets the number of `TRUE` values for an expression. |
| [`COVAR_POP`](statistical_aggregate_functions.md#covar_pop) | Computes the population covariance of a set of number pairs. |
| [`COVAR_SAMP`](statistical_aggregate_functions.md#covar_samp) | Computes the sample covariance of a set of number pairs. |
| [`CSC`](mathematical_functions.md#csc) | Computes the cosecant of `X`. |
| [`CSCH`](mathematical_functions.md#csch) | Computes the hyperbolic cosecant of `X`. |
| [`CUME_DIST`](numbering_functions.md#cume_dist) | Gets the cumulative distribution (relative position (0,1\]) of each row within a window. |
| [`CURRENT_DATE`](date_functions.md#current_date) | Returns the current date as a `DATE` value. |
| [`CURRENT_DATETIME`](datetime_functions.md#current_datetime) | Returns the current date and time as a `DATETIME` value. |
| [`CURRENT_TIME`](time_functions.md#current_time) | Returns the current time as a `TIME` value. |
| [`CURRENT_TIMESTAMP`](timestamp_functions.md#current_timestamp) | Returns the current date and time as a `TIMESTAMP` object. |
| [`DATE`](date_functions.md#date) | Constructs a `DATE` value. |
| [`DATE_ADD`](date_functions.md#date_add) | Adds a specified time interval to a `DATE` value. |
| [`DATE_BUCKET`](time-series-functions.md#date_bucket) | Gets the lower bound of the date bucket that contains a date. |
| [`DATE_DIFF`](date_functions.md#date_diff) | Gets the number of unit boundaries between two `DATE` values at a particular time granularity. |
| [`DATE_FROM_UNIX_DATE`](date_functions.md#date_from_unix_date) | Interprets an `INT64` expression as the number of days since 1970-01-01. |
| [`DATE_SUB`](date_functions.md#date_sub) | Subtracts a specified time interval from a `DATE` value. |
| [`DATE_TRUNC`](date_functions.md#date_trunc) | Truncates a `DATE`, `DATETIME`, or `TIMESTAMP` value at a particular granularity. |
| [`DATETIME`](datetime_functions.md#datetime) | Constructs a `DATETIME` value. |
| [`DATETIME_ADD`](datetime_functions.md#datetime_add) | Adds a specified time interval to a `DATETIME` value. |
| [`DATETIME_BUCKET`](time-series-functions.md#datetime_bucket) | Gets the lower bound of the datetime bucket that contains a datetime. |
| [`DATETIME_DIFF`](datetime_functions.md#datetime_diff) | Gets the number of unit boundaries between two `DATETIME` values at a particular time granularity. |
| [`DATETIME_SUB`](datetime_functions.md#datetime_sub) | Subtracts a specified time interval from a `DATETIME` value. |
| [`DATETIME_TRUNC`](datetime_functions.md#datetime_trunc) | Truncates a `DATETIME` or `TIMESTAMP` value at a particular granularity. |
| [`DENSE_RANK`](numbering_functions.md#dense_rank) | Gets the dense rank (1-based, no gaps) of each row within a window. |
| [`DESTINATION_NODE_ID`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#destination_node_id) | Gets a unique identifier of a graph edge's destination node. |
| [`DETERMINISTIC_DECRYPT_BYTES`](aead_encryption_functions.md#deterministic_decrypt_bytes) | Uses the matching key from a keyset to decrypt a `BYTES` ciphertext, using deterministic AEAD. |
| [`DETERMINISTIC_DECRYPT_STRING`](aead_encryption_functions.md#deterministic_decrypt_string) | Uses the matching key from a keyset to decrypt a `BYTES` ciphertext into a `STRING` plaintext, using deterministic AEAD. |
| [`DETERMINISTIC_ENCRYPT`](aead_encryption_functions.md#deterministic_encrypt) | Encrypts `STRING` plaintext, using the primary cryptographic key in a keyset, using deterministic AEAD encryption. |
| [`DIV`](mathematical_functions.md#div) | Divides integer `X` by integer `Y`. |
| [`DLP_DETERMINISTIC_ENCRYPT`](dlp_functions.md#dlp_deterministic_encrypt) | Encrypts data with a DLP compatible algorithm. |
| [`DLP_DETERMINISTIC_DECRYPT`](dlp_functions.md#dlp_deterministic_decrypt) | Decrypts DLP-encrypted data. |
| [`DLP_KEY_CHAIN`](dlp_functions.md#dlp_key_chain) | Gets a data encryption key that's wrapped by Cloud Key Management Service. |
| [`FLOAT64`](json_functions.md#double_for_json) | Converts a JSON number to a SQL `FLOAT64` value. |
| [`EDGES`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#edges) | Gets the edges in a graph path. The resulting array retains the original order in the graph path. |
| [`EDIT_DISTANCE`](string_functions.md#edit_distance) | Computes the Levenshtein distance between two `STRING` or `BYTES` values. |
| [`ELEMENT_ID`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#element_id) | Gets a graph element's unique identifier. |
| [`ENDS_WITH`](string_functions.md#ends_with) | Checks if a `STRING` or `BYTES` value is the suffix of another value. |
| [`ERROR`](debugging_functions.md#error) | Produces an error with a custom error message. |
| [`EXP`](mathematical_functions.md#exp) | Computes `e` to the power of `X`. |
| [`EXTERNAL_OBJECT_TRANSFORM`](table-functions-built-in.md#external_object_transform) | Produces an object table with the original columns plus one or more additional columns. |
| [`EXTERNAL_QUERY`](federated_query_functions.md#external_query) | Executes a query on an external database and returns the results as a temporary table. |
| [`EXTRACT`](date_functions.md#extract) | Extracts part of a date from a `DATE` value. |
| [`EXTRACT`](datetime_functions.md#extract) | Extracts part of a date and time from a `DATETIME` value. |
| [`EXTRACT`](interval_functions.md#extract) | Extracts part of an `INTERVAL` value. |
| [`EXTRACT`](time_functions.md#extract) | Extracts part of a `TIME` value. |
| [`EXTRACT`](timestamp_functions.md#extract) | Extracts part of a `TIMESTAMP` value. |
| [`EUCLIDEAN_DISTANCE`](mathematical_functions.md#euclidean_distance) | Computes the Euclidean distance between two vectors. |
| [`FARM_FINGERPRINT`](hash_functions.md#farm_fingerprint) | Computes the fingerprint of a `STRING` or `BYTES` value, using the FarmHash Fingerprint64 algorithm. |
| [`FIRST_VALUE`](navigation_functions.md#first_value) | Gets a value for the first row in the current window frame. |
| [`FLOOR`](mathematical_functions.md#floor) | Gets the largest integral value that isn't greater than `X`. |
| [`FORMAT_DATE`](date_functions.md#format_date) | Formats a `DATE` value according to a specified format string. |
| [`FORMAT_DATETIME`](datetime_functions.md#format_datetime) | Formats a `DATETIME` value according to a specified format string. |
| [`FORMAT_TIME`](time_functions.md#format_time) | Formats a `TIME` value according to the specified format string. |
| [`FORMAT_TIMESTAMP`](timestamp_functions.md#format_timestamp) | Formats a `TIMESTAMP` value according to the specified format string. |
| [`FORMAT`](string_functions.md#format_string) | Formats data and produces the results as a `STRING` value. |
| [`FROM_BASE32`](string_functions.md#from_base32) | Converts a base32-encoded `STRING` value into a `BYTES` value. |
| [`FROM_BASE64`](string_functions.md#from_base64) | Converts a base64-encoded `STRING` value into a `BYTES` value. |
| [`FROM_HEX`](string_functions.md#from_hex) | Converts a hexadecimal-encoded `STRING` value into a `BYTES` value. |
| [`GAP_FILL`](time-series-functions.md#gap_fill) | Finds and fills gaps in a time series. |
| [`GENERATE_ARRAY`](array_functions.md#generate_array) | Generates an array of values in a range. |
| [`GENERATE_DATE_ARRAY`](array_functions.md#generate_date_array) | Generates an array of dates in a range. |
| [`GENERATE_RANGE_ARRAY`](range-functions.md#generate_range_array) | Splits a range into an array of subranges. |
| [`GENERATE_TIMESTAMP_ARRAY`](array_functions.md#generate_timestamp_array) | Generates an array of timestamps in a range. |
| [`GENERATE_UUID`](utility-functions.md#generate_uuid) | Produces a random universally unique identifier (UUID) as a `STRING` value. |
| [`GREATEST`](mathematical_functions.md#greatest) | Gets the greatest value among `X1,...,XN`. |
| [`GROUPING`](aggregate_functions.md#grouping) | Checks if a groupable value in the `GROUP BY` clause is aggregated. |
| [`HLL_COUNT.EXTRACT`](hll_functions.md#hll_countextract) | Extracts a cardinality estimate of an HLL++ sketch. |
| [`HLL_COUNT.INIT`](hll_functions.md#hll_countinit) | Aggregates values of the same underlying type into a new HLL++ sketch. |
| [`HLL_COUNT.MERGE`](hll_functions.md#hll_countmerge) | Merges HLL++ sketches of the same underlying type into a new sketch, and then gets the cardinality of the new sketch. |
| [`HLL_COUNT.MERGE_PARTIAL`](hll_functions.md#hll_countmerge_partial) | Merges HLL++ sketches of the same underlying type into a new sketch. |
| [`IEEE_DIVIDE`](mathematical_functions.md#ieee_divide) | Divides `X` by `Y`, but doesn't generate errors for division by zero or overflow. |
| [`INITCAP`](string_functions.md#initcap) | Formats a `STRING` as proper case, which means that the first character in each word is uppercase and all other characters are lowercase. |
| [`INSTR`](string_functions.md#instr) | Finds the position of a subvalue inside another value, optionally starting the search at a given offset or occurrence. |
| [`INT64`](json_functions.md#int64_for_json) | Converts a JSON number to a SQL `INT64` value. |
| [`IS_ACYCLIC`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#is_acyclic) | Checks if a graph path has a repeating node. |
| [`IS_INF`](mathematical_functions.md#is_inf) | Checks if `X` is positive or negative infinity. |
| [`IS_NAN`](mathematical_functions.md#is_nan) | Checks if `X` is a `NaN` value. |
| [`IS_SIMPLE`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#is_simple) | Checks if a graph path is simple. |
| [`IS_TRAIL`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#is_trail) | Checks if a graph path has a repeating edge. |
| [`JSON_ARRAY`](json_functions.md#json_array) | Creates a JSON array. |
| [`JSON_ARRAY_APPEND`](json_functions.md#json_array_append) | Appends JSON data to the end of a JSON array. |
| [`JSON_ARRAY_INSERT`](json_functions.md#json_array_insert) | Inserts JSON data into a JSON array. |
| [`JSON_EXTRACT`](json_functions.md#json_extract) | (Deprecated) Extracts a JSON value and converts it to a SQL JSON-formatted `STRING` or `JSON` value. |
| [`JSON_EXTRACT_ARRAY`](json_functions.md#json_extract_array) | (Deprecated) Extracts a JSON array and converts it to a SQL `ARRAY<JSON-formatted STRING>` or `ARRAY<JSON>` value. |
| [`JSON_EXTRACT_SCALAR`](json_functions.md#json_extract_scalar) | (Deprecated) Extracts a JSON scalar value and converts it to a SQL `STRING` value. |
| [`JSON_EXTRACT_STRING_ARRAY`](json_functions.md#json_extract_string_array) | (Deprecated) Extracts a JSON array of scalar values and converts it to a SQL `ARRAY<STRING>` value. |
| [`JSON_FLATTEN`](json_functions.md#json_flatten) | Produces a new SQL `ARRAY<JSON>` value containing all non-array values that are either directly in the input JSON value or children of one or more consecutively nested arrays in the input JSON value. |
| [`JSON_KEYS`](json_functions.md#json_keys) | Extracts unique JSON keys from a JSON expression. |
| [`JSON_OBJECT`](json_functions.md#json_object) | Creates a JSON object. |
| [`JSON_QUERY`](json_functions.md#json_query) | Extracts a JSON value and converts it to a SQL JSON-formatted `STRING` or `JSON` value. |
| [`JSON_QUERY_ARRAY`](json_functions.md#json_query_array) | Extracts a JSON array and converts it to a SQL `ARRAY<JSON-formatted STRING>` or `ARRAY<JSON>` value. |
| [`JSON_REMOVE`](json_functions.md#json_remove) | Produces JSON with the specified JSON data removed. |
| [`JSON_SET`](json_functions.md#json_set) | Inserts or replaces JSON data. |
| [`JSON_STRIP_NULLS`](json_functions.md#json_strip_nulls) | Removes JSON nulls from JSON objects and JSON arrays. |
| [`JSON_TYPE`](json_functions.md#json_type) | Gets the JSON type of the outermost JSON value and converts the name of this type to a SQL `STRING` value. |
| [`JSON_VALUE`](json_functions.md#json_value) | Extracts a JSON scalar value and converts it to a SQL `STRING` value. |
| [`JSON_VALUE_ARRAY`](json_functions.md#json_value_array) | Extracts a JSON array of scalar values and converts it to a SQL `ARRAY<STRING>` value. |
| [`JUSTIFY_DAYS`](interval_functions.md#justify_days) | Normalizes the day part of an `INTERVAL` value. |
| [`JUSTIFY_HOURS`](interval_functions.md#justify_hours) | Normalizes the time part of an `INTERVAL` value. |
| [`JUSTIFY_INTERVAL`](interval_functions.md#justify_interval) | Normalizes the day and time parts of an `INTERVAL` value. |
| [`KEYS.ADD_KEY_FROM_RAW_BYTES`](aead_encryption_functions.md#keysadd_key_from_raw_bytes) | Adds a key to a keyset, and return the new keyset as a serialized `BYTES` value. |
| [`KEYS.KEYSET_CHAIN`](aead_encryption_functions.md#keyskeyset_chain) | Produces a Tink keyset that's encrypted with a Cloud KMS key. |
| [`KEYS.KEYSET_FROM_JSON`](aead_encryption_functions.md#keyskeyset_from_json) | Converts a `STRING` JSON keyset to a serialized `BYTES` value. |
| [`KEYS.KEYSET_LENGTH`](aead_encryption_functions.md#keyskeyset_length) | Gets the number of keys in the provided keyset. |
| [`KEYS.KEYSET_TO_JSON`](aead_encryption_functions.md#keyskeyset_to_json) | Gets a JSON `STRING` representation of a keyset. |
| [`KEYS.NEW_KEYSET`](aead_encryption_functions.md#keysnew_keyset) | Gets a serialized keyset containing a new key based on the key type. |
| [`KEYS.NEW_WRAPPED_KEYSET`](aead_encryption_functions.md#keysnew_wrapped_keyset) | Creates a new keyset and encrypts it with a Cloud KMS key. |
| [`KEYS.REWRAP_KEYSET`](aead_encryption_functions.md#keysrewrap_keyset) | Re-encrypts a wrapped keyset with a new Cloud KMS key. |
| [`KEYS.ROTATE_KEYSET`](aead_encryption_functions.md#keysrotate_keyset) | Adds a new primary cryptographic key to a keyset, based on the key type. |
| [`KEYS.ROTATE_WRAPPED_KEYSET`](aead_encryption_functions.md#keysrotate_wrapped_keyset) | Rewraps a keyset and rotates it. |
| [`KLL_QUANTILES.EXTRACT_INT64`](kll_functions.md#kll_quantilesextract_int64) | Gets a selected number of quantiles from an `INT64`-initialized KLL sketch. |
| [`KLL_QUANTILES.EXTRACT_FLOAT64`](kll_functions.md#kll_quantilesextract_double) | Gets a selected number of quantiles from a `FLOAT64`-initialized KLL sketch. |
| [`KLL_QUANTILES.EXTRACT_POINT_INT64`](kll_functions.md#kll_quantilesextract_point_int64) | Gets a specific quantile from an `INT64`-initialized KLL sketch. |
| [`KLL_QUANTILES.EXTRACT_POINT_FLOAT64`](kll_functions.md#kll_quantilesextract_point_double) | Gets a specific quantile from a `FLOAT64`-initialized KLL sketch. |
| [`KLL_QUANTILES.INIT_INT64`](kll_functions.md#kll_quantilesinit_int64) | Aggregates values into an `INT64`-initialized KLL sketch. |
| [`KLL_QUANTILES.INIT_FLOAT64`](kll_functions.md#kll_quantilesinit_double) | Aggregates values into a `FLOAT64`-initialized KLL sketch. |
| [`KLL_QUANTILES.MERGE_INT64`](kll_functions.md#kll_quantilesmerge_int64) | Merges `INT64`-initialized KLL sketches into a new sketch, and then gets the quantiles from the new sketch. |
| [`KLL_QUANTILES.MERGE_FLOAT64`](kll_functions.md#kll_quantilesmerge_double) | Merges `FLOAT64`-initialized KLL sketches into a new sketch, and then gets the quantiles from the new sketch. |
| [`KLL_QUANTILES.MERGE_PARTIAL`](kll_functions.md#kll_quantilesmerge_partial) | Merges KLL sketches of the same underlying type into a new sketch. |
| [`KLL_QUANTILES.MERGE_POINT_INT64`](kll_functions.md#kll_quantilesmerge_point_int64) | Merges `INT64`-initialized KLL sketches into a new sketch, and then gets a specific quantile from the new sketch. |
| [`KLL_QUANTILES.MERGE_POINT_FLOAT64`](kll_functions.md#kll_quantilesmerge_point_double) | Merges `FLOAT64`-initialized KLL sketches into a new sketch, and then gets a specific quantile from the new sketch. |
| [`LABELS`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#labels) | Gets the labels associated with a graph element. |
| [`LAG`](navigation_functions.md#lag) | Gets a value for a preceding row. |
| [`LAST_DAY`](date_functions.md#last_day) | Gets the last day in a specified time period that contains a `DATE` value. |
| [`LAST_DAY`](datetime_functions.md#last_day) | Gets the last day in a specified time period that contains a `DATETIME` value. |
| [`LAST_VALUE`](navigation_functions.md#last_value) | Gets a value for the last row in the current window frame. |
| [`LAX_BOOL`](json_functions.md#lax_bool) | Attempts to convert a JSON value to a SQL `BOOL` value. |
| [`LAX_FLOAT64`](json_functions.md#lax_double) | Attempts to convert a JSON value to a SQL `FLOAT64` value. |
| [`LAX_INT64`](json_functions.md#lax_int64) | Attempts to convert a JSON value to a SQL `INT64` value. |
| [`LAX_STRING`](json_functions.md#lax_string) | Attempts to convert a JSON value to a SQL `STRING` value. |
| [`LEAD`](navigation_functions.md#lead) | Gets a value for a subsequent row. |
| [`LEAST`](mathematical_functions.md#least) | Gets the least value among `X1,...,XN`. |
| [`LEFT`](string_functions.md#left) | Gets the specified leftmost portion from a `STRING` or `BYTES` value. |
| [`LENGTH`](string_functions.md#length) | Gets the length of a `STRING` or `BYTES` value. |
| [`LN`](mathematical_functions.md#ln) | Computes the natural logarithm of `X`. |
| [`LOG`](mathematical_functions.md#log) | Computes the natural logarithm of `X` or the logarithm of `X` to base `Y`. |
| [`LOG10`](mathematical_functions.md#log10) | Computes the natural logarithm of `X` to base 10. |
| [`LOGICAL_AND`](aggregate_functions.md#logical_and) | Gets the logical AND of all non-`NULL` expressions. |
| [`LOGICAL_OR`](aggregate_functions.md#logical_or) | Gets the logical OR of all non-`NULL` expressions. |
| [`LOWER`](string_functions.md#lower) | Formats alphabetic characters in a `STRING` value as lowercase. <br /> Formats ASCII characters in a `BYTES` value as lowercase. |
| [`LPAD`](string_functions.md#lpad) | Prepends a `STRING` or `BYTES` value with a pattern. |
| [`LTRIM`](string_functions.md#ltrim) | Identical to the `TRIM` function, but only removes leading characters. |
| [`MAKE_INTERVAL`](interval_functions.md#make_interval) | Constructs an `INTERVAL` value. |
| [`MAX`](aggregate_functions.md#max) | Gets the maximum non-`NULL` value. |
| [`MAX_BY`](aggregate_functions.md#max_by) | Synonym for `ANY_VALUE(x HAVING MAX y)`. |
| [`MD5`](hash_functions.md#md5) | Computes the hash of a `STRING` or `BYTES` value, using the MD5 algorithm. |
| [`MIN`](aggregate_functions.md#min) | Gets the minimum non-`NULL` value. |
| [`MIN_BY`](aggregate_functions.md#min_by) | Synonym for `ANY_VALUE(x HAVING MIN y)`. |
| [`MOD`](mathematical_functions.md#mod) | Gets the remainder of the division of `X` by `Y`. |
| [`NET.HOST`](net_functions.md#nethost) | Gets the hostname from a URL. |
| [`NET.IP_FROM_STRING`](net_functions.md#netip_from_string) | Converts an IPv4 or IPv6 address from a `STRING` value to a `BYTES` value in network byte order. |
| [`NET.IP_NET_MASK`](net_functions.md#netip_net_mask) | Gets a network mask. |
| [`NET.IP_TO_STRING`](net_functions.md#netip_to_string) | Converts an IPv4 or IPv6 address from a `BYTES` value in network byte order to a `STRING` value. |
| [`NET.IP_TRUNC`](net_functions.md#netip_trunc) | Converts a `BYTES` IPv4 or IPv6 address in network byte order to a `BYTES` subnet address. |
| [`NET.IPV4_FROM_INT64`](net_functions.md#netipv4_from_int64) | Converts an IPv4 address from an `INT64` value to a `BYTES` value in network byte order. |
| [`NET.IPV4_TO_INT64`](net_functions.md#netipv4_to_int64) | Converts an IPv4 address from a `BYTES` value in network byte order to an `INT64` value. |
| [`NET.PUBLIC_SUFFIX`](net_functions.md#netpublic_suffix) | Gets the public suffix from a URL. |
| [`NET.REG_DOMAIN`](net_functions.md#netreg_domain) | Gets the registered or registrable domain from a URL. |
| [`NET.SAFE_IP_FROM_STRING`](net_functions.md#netsafe_ip_from_string) | Similar to the `NET.IP_FROM_STRING`, but returns `NULL` instead of producing an error if the input is invalid. |
| [`NODES`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#nodes) | Gets the nodes in a graph path. The resulting array retains the original order in the graph path. |
| [`NORMALIZE`](string_functions.md#normalize) | Case-sensitively normalizes the characters in a `STRING` value. |
| [`NORMALIZE_AND_CASEFOLD`](string_functions.md#normalize_and_casefold) | Case-insensitively normalizes the characters in a `STRING` value. |
| [`NTH_VALUE`](navigation_functions.md#nth_value) | Gets a value for the Nth row of the current window frame. |
| [`NTILE`](numbering_functions.md#ntile) | Gets the quantile bucket number (1-based) of each row within a window. |
| [`OBJ.FETCH_METADATA`](objectref_functions.md#objfetch_metadata) | Fetches Cloud Storage metadata for a partially populated `ObjectRef` value. |
| [`OBJ.GET_ACCESS_URL`](objectref_functions.md#objget_access_url) | Returns access URLs for a Cloud Storage object. |
| [`OBJ.GET_READ_URL`](objectref_functions.md#objget_read_url) | Returns a read URL and status for a Cloud Storage object. |
| [`OBJ.MAKE_REF`](objectref_functions.md#objmake_ref) | Creates an `ObjectRef` value that contains reference information for a Cloud Storage object. |
| [`OCTET_LENGTH`](string_functions.md#octet_length) | Alias for `BYTE_LENGTH`. |
| [`PARSE_BIGNUMERIC`](conversion_functions.md#parse_bignumeric) | Converts a `STRING` value to a `BIGNUMERIC` value. |
| [`PARSE_DATE`](date_functions.md#parse_date) | Converts a `STRING` value to a `DATE` value. |
| [`PARSE_DATETIME`](datetime_functions.md#parse_datetime) | Converts a `STRING` value to a `DATETIME` value. |
| [`PARSE_JSON`](json_functions.md#parse_json) | Converts a JSON-formatted `STRING` value to a `JSON` value. |
| [`PARSE_NUMERIC`](conversion_functions.md#parse_numeric) | Converts a `STRING` value to a `NUMERIC` value. |
| [`PARSE_TIME`](time_functions.md#parse_time) | Converts a `STRING` value to a `TIME` value. |
| [`PARSE_TIMESTAMP`](timestamp_functions.md#parse_timestamp) | Converts a `STRING` value to a `TIMESTAMP` value. |
| [`PATH_FIRST`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#path_first) | Gets the first node in a graph path. |
| [`PATH_LAST`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#path_last) | Gets the last node in a graph path. |
| [`PATH_LENGTH`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#path_length) | Gets the number of edges in a graph path. |
| [`PERCENT_RANK`](numbering_functions.md#percent_rank) | Gets the percentile rank (from 0 to 1) of each row within a window. |
| [`PERCENTILE_CONT`](navigation_functions.md#percentile_cont) | Computes the specified percentile for a value, using linear interpolation. |
| [`PERCENTILE_CONT` (Differential Privacy)](aggregate-dp-functions.md#dp_percentile_cont) | `DIFFERENTIAL_PRIVACY`-supported `PERCENTILE_CONT`. Computes a differentially-private percentile across privacy unit columns in a query with a `DIFFERENTIAL_PRIVACY` clause. |
| [`PERCENTILE_DISC`](navigation_functions.md#percentile_disc) | Computes the specified percentile for a discrete value. |
| [`POW`](mathematical_functions.md#pow) | Produces the value of `X` raised to the power of `Y`. |
| [`POWER`](mathematical_functions.md#power) | Synonym of `POW`. |
| [`RAND`](mathematical_functions.md#rand) | Generates a pseudo-random value of type `FLOAT64` in the range of `[0, 1)`. |
| [`RANGE`](range-functions.md#range) | Constructs a range of `DATE`, `DATETIME`, or `TIMESTAMP` values. |
| [`RANGE_BUCKET`](mathematical_functions.md#range_bucket) | Scans through a sorted array and returns the 0-based position of a point's upper bound. |
| [`RANGE_CONTAINS`](range-functions.md#range_contains) | Signature 1: Checks if one range is in another range. <br /> Signature 2: Checks if a value is in a range. |
| [`RANGE_END`](range-functions.md#range_end) | Gets the upper bound of a range. |
| [`RANGE_INTERSECT`](range-functions.md#range_intersect) | Gets a segment of two ranges that intersect. |
| [`RANGE_OVERLAPS`](range-functions.md#range_overlaps) | Checks if two ranges overlap. |
| [`RANGE_SESSIONIZE`](range-functions.md#range_sessionize) | Produces a table of sessionized ranges. |
| [`RANGE_START`](range-functions.md#range_start) | Gets the lower bound of a range. |
| [`RANK`](numbering_functions.md#rank) | Gets the rank (1-based) of each row within a window. |
| [`REGEXP_CONTAINS`](string_functions.md#regexp_contains) | Checks if a value is a partial match for a regular expression. |
| [`REGEXP_EXTRACT`](string_functions.md#regexp_extract) | Produces a substring that matches a regular expression. |
| [`REGEXP_EXTRACT_ALL`](string_functions.md#regexp_extract_all) | Produces an array of all substrings that match a regular expression. |
| [`REGEXP_INSTR`](string_functions.md#regexp_instr) | Finds the position of a regular expression match in a value, optionally starting the search at a given offset or occurrence. |
| [`REGEXP_REPLACE`](string_functions.md#regexp_replace) | Produces a `STRING` value where all substrings that match a regular expression are replaced with a specified value. |
| [`REGEXP_SUBSTR`](string_functions.md#regexp_substr) | Synonym for `REGEXP_EXTRACT`. |
| [`REPEAT`](string_functions.md#repeat) | Produces a `STRING` or `BYTES` value that consists of an original value, repeated. |
| [`REPLACE`](string_functions.md#replace) | Replaces all occurrences of a pattern with another pattern in a `STRING` or `BYTES` value. |
| [`REVERSE`](string_functions.md#reverse) | Reverses a `STRING` or `BYTES` value. |
| [`RIGHT`](string_functions.md#right) | Gets the specified rightmost portion from a `STRING` or `BYTES` value. |
| [`ROUND`](mathematical_functions.md#round) | Rounds `X` to the nearest integer or rounds `X` to `N` decimal places after the decimal point. |
| [`ROW_NUMBER`](numbering_functions.md#row_number) | Gets the sequential row number (1-based) of each row within a window. |
| [`RPAD`](string_functions.md#rpad) | Appends a `STRING` or `BYTES` value with a pattern. |
| [`RTRIM`](string_functions.md#rtrim) | Identical to the `TRIM` function, but only removes trailing characters. |
| [`S2_CELLIDFROMPOINT`](geography_functions.md#s2_cellidfrompoint) | Gets the S2 cell ID covering a point `GEOGRAPHY` value. |
| [`S2_COVERINGCELLIDS`](geography_functions.md#s2_coveringcellids) | Gets an array of S2 cell IDs that cover a `GEOGRAPHY` value. |
| [`SAFE_ADD`](mathematical_functions.md#safe_add) | Equivalent to the addition operator (`X + Y`), but returns `NULL` if overflow occurs. |
| [`SAFE_CAST`](conversion_functions.md#safe_casting) | Similar to the `CAST` function, but returns `NULL` when a runtime error is produced. |
| [`SAFE_CONVERT_BYTES_TO_STRING`](string_functions.md#safe_convert_bytes_to_string) | Converts a `BYTES` value to a `STRING` value and replace any invalid UTF-8 characters with the Unicode replacement character, `U+FFFD`. |
| [`SAFE_DIVIDE`](mathematical_functions.md#safe_divide) | Equivalent to the division operator (`X / Y`), but returns `NULL` if an error occurs. |
| [`SAFE_MULTIPLY`](mathematical_functions.md#safe_multiply) | Equivalent to the multiplication operator (`X * Y`), but returns `NULL` if overflow occurs. |
| [`SAFE_NEGATE`](mathematical_functions.md#safe_negate) | Equivalent to the unary minus operator (`-X`), but returns `NULL` if overflow occurs. |
| [`SAFE_SUBTRACT`](mathematical_functions.md#safe_subtract) | Equivalent to the subtraction operator (`X - Y`), but returns `NULL` if overflow occurs. |
| [`SEARCH`](search_functions.md#search) | Checks to see whether a table or other search data contains a set of search terms. |
| [`SEC`](mathematical_functions.md#sec) | Computes the secant of `X`. |
| [`SECH`](mathematical_functions.md#sech) | Computes the hyperbolic secant of `X`. |
| [`SESSION_USER`](security_functions.md#session_user) | Get the email address or principal identifier of the user that's running the query. |
| [`SHA1`](hash_functions.md#sha1) | Computes the hash of a `STRING` or `BYTES` value, using the SHA-1 algorithm. |
| [`SHA256`](hash_functions.md#sha256) | Computes the hash of a `STRING` or `BYTES` value, using the SHA-256 algorithm. |
| [`SHA512`](hash_functions.md#sha512) | Computes the hash of a `STRING` or `BYTES` value, using the SHA-512 algorithm. |
| [`SIGN`](mathematical_functions.md#sign) | Produces -1 , 0, or +1 for negative, zero, and positive arguments respectively. |
| [`SIN`](mathematical_functions.md#sin) | Computes the sine of `X`. |
| [`SINH`](mathematical_functions.md#sinh) | Computes the hyperbolic sine of `X`. |
| [`SOURCE_NODE_ID`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-functions#source_node_id) | Gets a unique identifier of a graph edge's source node. |
| [`SOUNDEX`](string_functions.md#soundex) | Gets the Soundex codes for words in a `STRING` value. |
| [`SPLIT`](string_functions.md#split) | Splits a `STRING` or `BYTES` value, using a delimiter. |
| [`SQRT`](mathematical_functions.md#sqrt) | Computes the square root of `X`. |
| [`ST_ANGLE`](geography_functions.md#st_angle) | Takes three point `GEOGRAPHY` values, which represent two intersecting lines, and returns the angle between these lines. |
| [`ST_AREA`](geography_functions.md#st_area) | Gets the area covered by the polygons in a `GEOGRAPHY` value. |
| [`ST_ASBINARY`](geography_functions.md#st_asbinary) | Converts a `GEOGRAPHY` value to a `BYTES` WKB geography value. |
| [`ST_ASGEOJSON`](geography_functions.md#st_asgeojson) | Converts a `GEOGRAPHY` value to a `STRING` GeoJSON geography value. |
| [`ST_ASTEXT`](geography_functions.md#st_astext) | Converts a `GEOGRAPHY` value to a `STRING` WKT geography value. |
| [`ST_AZIMUTH`](geography_functions.md#st_azimuth) | Gets the azimuth of a line segment formed by two point `GEOGRAPHY` values. |
| [`ST_BOUNDARY`](geography_functions.md#st_boundary) | Gets the union of component boundaries in a `GEOGRAPHY` value. |
| [`ST_BOUNDINGBOX`](geography_functions.md#st_boundingbox) | Gets the bounding box for a `GEOGRAPHY` value. |
| [`ST_BUFFER`](geography_functions.md#st_buffer) | Gets the buffer around a `GEOGRAPHY` value, using a specific number of segments. |
| [`ST_BUFFERWITHTOLERANCE`](geography_functions.md#st_bufferwithtolerance) | Gets the buffer around a `GEOGRAPHY` value, using tolerance. |
| [`ST_CENTROID`](geography_functions.md#st_centroid) | Gets the centroid of a `GEOGRAPHY` value. |
| [`ST_CENTROID_AGG`](geography_functions.md#st_centroid_agg) | Gets the centroid of a set of `GEOGRAPHY` values. |
| [`ST_CLOSESTPOINT`](geography_functions.md#st_closestpoint) | Gets the point on a `GEOGRAPHY` value which is closest to any point in a second `GEOGRAPHY` value. |
| [`ST_CLUSTERDBSCAN`](geography_functions.md#st_clusterdbscan) | Performs DBSCAN clustering on a group of `GEOGRAPHY` values and produces a 0-based cluster number for this row. |
| [`ST_CONTAINS`](geography_functions.md#st_contains) | Checks if one `GEOGRAPHY` value contains another `GEOGRAPHY` value. |
| [`ST_CONVEXHULL`](geography_functions.md#st_convexhull) | Returns the convex hull for a `GEOGRAPHY` value. |
| [`ST_COVEREDBY`](geography_functions.md#st_coveredby) | Checks if all points of a `GEOGRAPHY` value are on the boundary or interior of another `GEOGRAPHY` value. |
| [`ST_COVERS`](geography_functions.md#st_covers) | Checks if all points of a `GEOGRAPHY` value are on the boundary or interior of another `GEOGRAPHY` value. |
| [`ST_DIFFERENCE`](geography_functions.md#st_difference) | Gets the point set difference between two `GEOGRAPHY` values. |
| [`ST_DIMENSION`](geography_functions.md#st_dimension) | Gets the dimension of the highest-dimensional element in a `GEOGRAPHY` value. |
| [`ST_DISJOINT`](geography_functions.md#st_disjoint) | Checks if two `GEOGRAPHY` values are disjoint (don't intersect). |
| [`ST_DISTANCE`](geography_functions.md#st_distance) | Gets the shortest distance in meters between two `GEOGRAPHY` values. |
| [`ST_DUMP`](geography_functions.md#st_dump) | Returns an array of simple `GEOGRAPHY` components in a `GEOGRAPHY` value. |
| [`ST_DWITHIN`](geography_functions.md#st_dwithin) | Checks if any points in two `GEOGRAPHY` values are within a given distance. |
| [`ST_ENDPOINT`](geography_functions.md#st_endpoint) | Gets the last point of a linestring `GEOGRAPHY` value. |
| [`ST_EQUALS`](geography_functions.md#st_equals) | Checks if two `GEOGRAPHY` values represent the same `GEOGRAPHY` value. |
| [`ST_EXTENT`](geography_functions.md#st_extent) | Gets the bounding box for a group of `GEOGRAPHY` values. |
| [`ST_EXTERIORRING`](geography_functions.md#st_exteriorring) | Returns a linestring `GEOGRAPHY` value that corresponds to the outermost ring of a polygon `GEOGRAPHY` value. |
| [`ST_GEOGFROM`](geography_functions.md#st_geogfrom) | Converts a `STRING` or `BYTES` value into a `GEOGRAPHY` value. |
| [`ST_GEOGFROMGEOJSON`](geography_functions.md#st_geogfromgeojson) | Converts a `STRING` GeoJSON geometry value into a `GEOGRAPHY` value. |
| [`ST_GEOGFROMTEXT`](geography_functions.md#st_geogfromtext) | Converts a `STRING` WKT geometry value into a `GEOGRAPHY` value. |
| [`ST_GEOGFROMWKB`](geography_functions.md#st_geogfromwkb) | Converts a `BYTES` or hexadecimal-text `STRING` WKT geometry value into a `GEOGRAPHY` value. |
| [`ST_GEOGPOINT`](geography_functions.md#st_geogpoint) | Creates a point `GEOGRAPHY` value for a given longitude and latitude. |
| [`ST_GEOGPOINTFROMGEOHASH`](geography_functions.md#st_geogpointfromgeohash) | Gets a point `GEOGRAPHY` value that's in the middle of a bounding box defined in a `STRING` GeoHash value. |
| [`ST_GEOHASH`](geography_functions.md#st_geohash) | Converts a point `GEOGRAPHY` value to a `STRING` GeoHash value. |
| [`ST_GEOMETRYTYPE`](geography_functions.md#st_geometrytype) | Gets the Open Geospatial Consortium (OGC) geometry type for a `GEOGRAPHY` value. |
| [`ST_HAUSDORFFDISTANCE`](geography_functions.md#st_hausdorffdistance) | Gets the discrete Hausdorff distance between two geometries. |
| [`ST_HAUSDORFFDWITHIN`](geography_functions.md#st_hausdorffdwithin) | Checks if the Hausdorff distance between two `GEOGRAPHY` values is within a given distance. |
| [`ST_INTERIORRINGS`](geography_functions.md#st_interiorrings) | Gets the interior rings of a polygon `GEOGRAPHY` value. |
| [`ST_INTERSECTION`](geography_functions.md#st_intersection) | Gets the point set intersection of two `GEOGRAPHY` values. |
| [`ST_INTERSECTS`](geography_functions.md#st_intersects) | Checks if at least one point appears in two `GEOGRAPHY` values. |
| [`ST_INTERSECTSBOX`](geography_functions.md#st_intersectsbox) | Checks if a `GEOGRAPHY` value intersects a rectangle. |
| [`ST_ISCLOSED`](geography_functions.md#st_isclosed) | Checks if all components in a `GEOGRAPHY` value are closed. |
| [`ST_ISCOLLECTION`](geography_functions.md#st_iscollection) | Checks if the total number of points, linestrings, and polygons is greater than one in a `GEOGRAPHY` value. |
| [`ST_ISEMPTY`](geography_functions.md#st_isempty) | Checks if a `GEOGRAPHY` value is empty. |
| [`ST_ISRING`](geography_functions.md#st_isring) | Checks if a `GEOGRAPHY` value is a closed, simple linestring. |
| [`ST_LENGTH`](geography_functions.md#st_length) | Gets the total length of lines in a `GEOGRAPHY` value. |
| [`ST_LINEINTERPOLATEPOINT`](geography_functions.md#st_lineinterpolatepoint) | Gets a point at a specific fraction in a linestring `GEOGRAPHY` value. |
| [`ST_LINELOCATEPOINT`](geography_functions.md#st_linelocatepoint) | Gets a section of a linestring `GEOGRAPHY` value between the start point and a point `GEOGRAPHY` value. |
| [`ST_LINESUBSTRING`](geography_functions.md#st_linesubstring) | Gets a segment of a single linestring at a specific starting and ending fraction. |
| [`ST_MAKELINE`](geography_functions.md#st_makeline) | Creates a linestring `GEOGRAPHY` value by concatenating the point and linestring vertices of `GEOGRAPHY` values. |
| [`ST_MAKEPOLYGON`](geography_functions.md#st_makepolygon) | Constructs a polygon `GEOGRAPHY` value by combining a polygon shell with polygon holes. |
| [`ST_MAKEPOLYGONORIENTED`](geography_functions.md#st_makepolygonoriented) | Constructs a polygon `GEOGRAPHY` value, using an array of linestring `GEOGRAPHY` values. The vertex ordering of each linestring determines the orientation of each polygon ring. |
| [`ST_MAXDISTANCE`](geography_functions.md#st_maxdistance) | Gets the longest distance between two non-empty `GEOGRAPHY` values. |
| [`ST_NPOINTS`](geography_functions.md#st_npoints) | An alias of `ST_NUMPOINTS`. |
| [`ST_NUMGEOMETRIES`](geography_functions.md#st_numgeometries) | Gets the number of geometries in a `GEOGRAPHY` value. |
| [`ST_NUMPOINTS`](geography_functions.md#st_numpoints) | Gets the number of vertices in the a `GEOGRAPHY` value. |
| [`ST_PERIMETER`](geography_functions.md#st_perimeter) | Gets the length of the boundary of the polygons in a `GEOGRAPHY` value. |
| [`ST_POINTN`](geography_functions.md#st_pointn) | Gets the point at a specific index of a linestring `GEOGRAPHY` value. |
| [`ST_REGIONSTATS`](geography_functions.md#st_regionstats) | Computes statistics describing the pixels in a geospatial raster image that intersect a `GEOGRAPHY` value. |
| [`ST_SIMPLIFY`](geography_functions.md#st_simplify) | Converts a `GEOGRAPHY` value into a simplified `GEOGRAPHY` value, using tolerance. |
| [`ST_SNAPTOGRID`](geography_functions.md#st_snaptogrid) | Produces a `GEOGRAPHY` value, where each vertex has been snapped to a longitude/latitude grid. |
| [`ST_STARTPOINT`](geography_functions.md#st_startpoint) | Gets the first point of a linestring `GEOGRAPHY` value. |
| [`ST_TOUCHES`](geography_functions.md#st_touches) | Checks if two `GEOGRAPHY` values intersect and their interiors have no elements in common. |
| [`ST_UNION`](geography_functions.md#st_union) | Gets the point set union of multiple `GEOGRAPHY` values. |
| [`ST_UNION_AGG`](geography_functions.md#st_union_agg) | Aggregates over `GEOGRAPHY` values and gets their point set union. |
| [`ST_WITHIN`](geography_functions.md#st_within) | Checks if one `GEOGRAPHY` value contains another `GEOGRAPHY` value. |
| [`ST_X`](geography_functions.md#st_x) | Gets the longitude from a point `GEOGRAPHY` value. |
| [`ST_Y`](geography_functions.md#st_y) | Gets the latitude from a point `GEOGRAPHY` value. |
| [`STARTS_WITH`](string_functions.md#starts_with) | Checks if a `STRING` or `BYTES` value is a prefix of another value. |
| [`STDDEV`](statistical_aggregate_functions.md#stddev) | An alias of the `STDDEV_SAMP` function. |
| [`STDDEV_POP`](statistical_aggregate_functions.md#stddev_pop) | Computes the population (biased) standard deviation of the values. |
| [`STDDEV_SAMP`](statistical_aggregate_functions.md#stddev_samp) | Computes the sample (unbiased) standard deviation of the values. |
| [`STRING` (JSON)](json_functions.md#string_for_json) | Converts a JSON string to a SQL `STRING` value. |
| [`STRING` (Timestamp)](timestamp_functions.md#string) | Converts a `TIMESTAMP` value to a `STRING` value. |
| [`STRING_AGG`](aggregate_functions.md#string_agg) | Concatenates non-`NULL` `STRING` or `BYTES` values. |
| [`STRPOS`](string_functions.md#strpos) | Finds the position of the first occurrence of a subvalue inside another value. |
| [`SUBSTR`](string_functions.md#substr) | Gets a portion of a `STRING` or `BYTES` value. |
| [`SUBSTRING`](string_functions.md#substring) | Alias for `SUBSTR` |
| [`SUM`](aggregate_functions.md#sum) | Gets the sum of non-`NULL` values. |
| [`SUM` (Differential Privacy)](aggregate-dp-functions.md#dp_sum) | `DIFFERENTIAL_PRIVACY`-supported `SUM`. Gets the differentially-private sum of non-`NULL`, non-`NaN` values in a query with a `DIFFERENTIAL_PRIVACY` clause. |
| [`TAN`](mathematical_functions.md#tan) | Computes the tangent of `X`. |
| [`TANH`](mathematical_functions.md#tanh) | Computes the hyperbolic tangent of `X`. |
| [`TEXT_ANALYZE`](text-analysis-functions.md#text_analyze) | Extracts terms (tokens) from text and converts them into a tokenized document. |
| [`TF_IDF`](text-analysis-functions.md#tf_idf) | Evaluates how relevant a term (token) is to a tokenized document in a set of tokenized documents. |
| [`TIME`](time_functions.md#time) | Constructs a `TIME` value. |
| [`TIME_ADD`](time_functions.md#time_add) | Adds a specified time interval to a `TIME` value. |
| [`TIME_DIFF`](time_functions.md#time_diff) | Gets the number of unit boundaries between two `TIME` values at a particular time granularity. |
| [`TIME_SUB`](time_functions.md#time_sub) | Subtracts a specified time interval from a `TIME` value. |
| [`TIME_TRUNC`](time_functions.md#time_trunc) | Truncates a `TIME` value at a particular granularity. |
| [`TIMESTAMP`](timestamp_functions.md#timestamp) | Constructs a `TIMESTAMP` value. |
| [`TIMESTAMP_ADD`](timestamp_functions.md#timestamp_add) | Adds a specified time interval to a `TIMESTAMP` value. |
| [`TIMESTAMP_BUCKET`](time-series-functions.md#timestamp_bucket) | Gets the lower bound of the timestamp bucket that contains a timestamp. |
| [`TIMESTAMP_DIFF`](timestamp_functions.md#timestamp_diff) | Gets the number of unit boundaries between two `TIMESTAMP` values at a particular time granularity. |
| [`TIMESTAMP_MICROS`](timestamp_functions.md#timestamp_micros) | Converts the number of microseconds since 1970-01-01 00:00:00 UTC to a `TIMESTAMP`. |
| [`TIMESTAMP_MILLIS`](timestamp_functions.md#timestamp_millis) | Converts the number of milliseconds since 1970-01-01 00:00:00 UTC to a `TIMESTAMP`. |
| [`TIMESTAMP_SECONDS`](timestamp_functions.md#timestamp_seconds) | Converts the number of seconds since 1970-01-01 00:00:00 UTC to a `TIMESTAMP`. |
| [`TIMESTAMP_SUB`](timestamp_functions.md#timestamp_sub) | Subtracts a specified time interval from a `TIMESTAMP` value. |
| [`TIMESTAMP_TRUNC`](timestamp_functions.md#timestamp_trunc) | Truncates a `TIMESTAMP` or `DATETIME` value at a particular granularity. |
| [`TO_BASE32`](string_functions.md#to_base32) | Converts a `BYTES` value to a base32-encoded `STRING` value. |
| [`TO_BASE64`](string_functions.md#to_base64) | Converts a `BYTES` value to a base64-encoded `STRING` value. |
| [`TO_CODE_POINTS`](string_functions.md#to_code_points) | Converts a `STRING` or `BYTES` value into an array of extended ASCII code points. |
| [`TO_HEX`](string_functions.md#to_hex) | Converts a `BYTES` value to a hexadecimal `STRING` value. |
| [`TO_JSON`](json_functions.md#to_json) | Converts a SQL value to a JSON value. |
| [`TO_JSON_STRING`](json_functions.md#to_json_string) | Converts a SQL value to a JSON-formatted `STRING` value. |
| [`TRANSLATE`](string_functions.md#translate) | Within a value, replaces each source character with the corresponding target character. |
| [`TRIM`](string_functions.md#trim) | Removes the specified leading and trailing Unicode code points or bytes from a `STRING` or `BYTES` value. |
| [`TRUNC`](mathematical_functions.md#trunc) | Rounds a number like `ROUND(X)` or `ROUND(X, N)`, but always rounds towards zero and never overflows. |
| [`TYPEOF`](utility-functions.md#typeof) | Gets the name of the data type for an expression. |
| [`UNICODE`](string_functions.md#unicode) | Gets the Unicode code point for the first character in a value. |
| [`UNIX_DATE`](date_functions.md#unix_date) | Converts a `DATE` value to the number of days since 1970-01-01. |
| [`UNIX_MICROS`](timestamp_functions.md#unix_micros) | Converts a `TIMESTAMP` value to the number of microseconds since 1970-01-01 00:00:00 UTC. |
| [`UNIX_MILLIS`](timestamp_functions.md#unix_millis) | Converts a `TIMESTAMP` value to the number of milliseconds since 1970-01-01 00:00:00 UTC. |
| [`UNIX_SECONDS`](timestamp_functions.md#unix_seconds) | Converts a `TIMESTAMP` value to the number of seconds since 1970-01-01 00:00:00 UTC. |
| [`UPPER`](string_functions.md#upper) | Formats alphabetic characters in a `STRING` value as uppercase. <br /> Formats ASCII characters in a `BYTES` value as uppercase. |
| [`VAR_POP`](statistical_aggregate_functions.md#var_pop) | Computes the population (biased) variance of the values. |
| [`VAR_SAMP`](statistical_aggregate_functions.md#var_samp) | Computes the sample (unbiased) variance of the values. |
| [`VARIANCE`](statistical_aggregate_functions.md#variance) | An alias of `VAR_SAMP`. |
| [`VECTOR_SEARCH`](search_functions.md#vector_search) | Performs a semantic search or a hybrid search on embeddings to find similar entities. |
| [`VECTOR_INDEX.STATISTICS`](vectorindex_functions.md#vector_indexstatistics) | Calculate how much an indexed table's data has drifted between when a vector index was trained and the present. |
<?php
/**
 * Fails when readme.txt's "Tested up to" header trails the current WordPress release.
 *
 * Registered as a pup simple check, so one file gates both a pull request, through
 * .github/workflows/check-tested-up-to.yml, and a production zip build, through the
 * `pup check` step in zip.yml. Repositories whose readme.txt carries no plugin header
 * block, tribe-common among them, pass without reaching the network.
 *
 * Available variables:
 *
 * @var Symfony\Component\Console\Input\InputInterface $input
 * @var \StellarWP\Pup\Command\Io                      $output
 * @var \StellarWP\Pup\Commands\Checks\SimpleCheck     $this
 *
 * The VIP performance sniffs below govern runtime plugin code serving a web request. This
 * runs in CI and in a release build, where the ten second timeout is the safer number: the
 * check fails closed, so a tighter one turns a merely slow api.wordpress.org into a blocked
 * release pull request across every repository at once.
 *
 * @phpcs:disable WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound, Squiz.Commenting.FileComment.MissingPackageTag, WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents, WordPressVIPMinimum.Performance.FetchingRemoteData.FileGetContentsRemoteFile, WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
 */

$github_base_ref = getenv( 'GITHUB_BASE_REF' );

/*
 * No base ref means no pull request is in play — a production zip build, or a local run —
 * and the header still has to be current. On a pull request it only matters on the
 * branches a release is cut from.
 */
if (
	is_string( $github_base_ref )
	&& '' !== $github_base_ref
	&& 'main' !== $github_base_ref
	&& 0 !== strpos( $github_base_ref, 'release/' )
) {
	$output->warning( sprintf( 'Skipping the "Tested up to" check: "%s" is neither main nor a release branch.', $github_base_ref ) );

	return 0;
}

/*
 * The header lives in readme.txt here; the main plugin file carries only "Requires at
 * least". tribe-common ships a changelog-only readme.txt with no header block and is in
 * the same sync group, so a missing header is a pass. Resolved before the API call so
 * those repositories never reach the network.
 */
if ( ! file_exists( 'readme.txt' ) ) {
	$output->warning( 'Skipping the "Tested up to" check: no readme.txt in this repository.' );

	return 0;
}

/* Anchored per line so a version quoted in the changelog body cannot pass for the header. */
preg_match( '/^Tested up to:\s*([0-9.]+)/m', file_get_contents( 'readme.txt' ), $matches );

$tested_up_to = $matches[1] ?? '';

if ( '' === $tested_up_to ) {
	$output->warning( 'Skipping the "Tested up to" check: readme.txt carries no "Tested up to" header.' );

	return 0;
}

/*
 * Ten seconds: the default socket timeout would hold a release pull request open for a
 * minute when api.wordpress.org is slow.
 */
$context  = stream_context_create( [ 'http' => [ 'timeout' => 10 ] ] );
$response = file_get_contents( 'https://api.wordpress.org/core/version-check/1.7/', false, $context );

if ( false === $response ) {
	$output->error( 'Failed to fetch the current WordPress version from api.wordpress.org.' );

	return 1;
}

$payload = json_decode( $response );
$latest  = $payload->offers[0]->version ?? '';

if ( '' === $latest ) {
	$output->error( 'The WordPress version-check API returned no version.' );

	return 1;
}

if ( version_compare( $tested_up_to, $latest, '<' ) ) {
	$output->error(
		sprintf(
			'The "Tested up to" header in readme.txt trails the current WordPress release. Found: %1$s, expected: %2$s. Run the "Release: Update WordPress Version" workflow with tested_up_to: %2$s.',
			$tested_up_to,
			$latest
		)
	);

	return 1;
}

$output->writeln( sprintf( 'readme.txt is tested up to %s; the current WordPress release is %s.', $tested_up_to, $latest ) );

return 0;

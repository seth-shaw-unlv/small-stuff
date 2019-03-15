<?php

/**
 * Run from the commandline using drush: `drush -l <site url> scr generate-image-service-files.php`
 */

use Drupal\Core\Session\UserSession;
use Drupal\user\Entity\User;
printf("STARTING:\t%d\n", time());
$userid = 1;
$account = User::load($userid);
$accountSwitcher = \Drupal::service('account_switcher');
$userSession = new UserSession([
  'uid'   => $account->id(),
  'name'  => $account->getUsername(),
  'roles' => $account->getRoles(),
]);
$accountSwitcher->switchTo($userSession);

printf("START ORIGINAL QUERY:\t%d\n", time());
$original_tid = reset(
    \Drupal::entityQuery('taxonomy_term')
      ->condition('field_external_uri', 'http://pcdm.org/use#OriginalFile')
      ->execute()
  );

// Tried using entityQuery for media to get the field_media_of value,
// but that took a long time and resorted in out of memory errors.
// The select query method is a *much* more efficient.

$originals_query = \Drupal::database()->select('media', 'm');
$originals_query->join('media__field_media_use', 'u', 'm.mid = u.entity_id');
$originals_query->join('media__field_media_of', 'o', 'm.mid = o.entity_id');
$originals_query->fields('o', ['field_media_of_target_id'])
  ->condition('u.field_media_use_target_id', $original_tid);
$nodes_w_originals = $originals_query->execute()->fetchCol();

printf("START SERVICE QUERY:\t%d\n", time());
$service_tid = reset(
    \Drupal::entityQuery('taxonomy_term')
      ->condition('field_external_uri', 'http://pcdm.org/use#ServiceFile')
      ->execute()
  );

$service_query = \Drupal::database()->select('media', 'm');
$service_query->join('media__field_media_use', 'u', 'm.mid = u.entity_id');
$service_query->join('media__field_media_of', 'o', 'm.mid = o.entity_id');
$service_query->fields('o', ['field_media_of_target_id'])
  ->condition('u.field_media_use_target_id', $service_tid);
$nodes_w_service = $service_query->execute()->fetchCol();

printf("COMPARE LISTS:\t%d\n", time());
$results = array_diff($nodes_w_originals, $nodes_w_service);

printf("BUILDING ACTIONS:\t%d\n", time());
$action = \Drupal\system\Entity\Action::load('image_generate_a_service_file_from_an_original_file');

// After the entityQuery of Media was replaced with select queries the need
// for a limit was unneccessary, but it may be useful if this is converted
// into a cron job later. Just setting it very high for the time-being.

$limit = 200000;
if($limit < count($results)) {
  printf("Only running %s on %d of %d possible.\n", $action->id(), $limit, count($results));
}
$to_run = array_slice($results, 0, $limit);

printf("STARTING ACTIONS:\t%d\n", time());

foreach ($to_run as $nid) {
  $node = \Drupal::entityTypeManager()->getStorage('node')->load($nid);
  printf("Performing '%s' on '%s' at %s\n", $action->id(), $node->toUrl()->toString(), date(DATE_ATOM));
  $action->execute([$node]);
}
printf("DONE ISSUING ACTIONS:\t%d\n", time());
$accountSwitcher->switchBack();

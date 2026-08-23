<script setup lang="ts">
const route = useRoute()

// Keep the query: the OAuth callback lands here with ?auth_error=<code>, and
// dropping it would make a failed sign-in look like nothing happened.
await navigateTo({ path: '/clients', query: route.query })
</script>
